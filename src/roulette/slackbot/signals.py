from django.db.models.signals import post_save
from django.dispatch import receiver
from matcher.models import Roulette, RouletteUser
from matcher.signals import post_matching
from .models import SlackRoulette, SlackUser
from .webapi import post_on_channel, post_on_thread, post_im_to_all_admins, post_im
from django.conf import settings
from django.utils import timezone


@receiver(post_save, sender=Roulette)
def broadcast_new_roulette(sender, instance, created, **kwargs):
    # When a roulette is created, create a new thread on Slack
    if not created:
        return
    try:
        thread_ts, channel_id = post_on_channel(settings.SLACK_CHANNEL, (
            "A new coffee roulette #{0} is going to start!"
            " If you want to participate, please reply in this thread.\n"
            "The voting deadline is {1}. Coffee will end on {2}\n"
        ).format(instance.pk, timezone.localtime(instance.vote_deadline), timezone.localtime(instance.coffee_deadline)))
        first_reply_ts = post_on_thread(channel_id, thread_ts,
                                        ("Please vote by writing YES or NO (case is ignored).\n"
                                         " If you make a typo or want to change your vote, just write again. Only the last vote will count.")
                                        )

    except Exception as exception:
        print(str(exception))
        try:
            post_im_to_all_admins("While saving the roulette #{0}, an error occured."
                                  " Consider fixing the issue and deleting the faulty roulette."
                                  " Error was:\n{1}".format(instance.pk, str(exception)))
        except Exception as nestedException:
            print(str(nestedException))
        return

    SlackRoulette.objects.create(roulette=instance, thread_timestamp=thread_ts,
                                 latest_response_timestamp=first_reply_ts, channel_id=channel_id)


def notify_matching_result(roulette, slack_user, other_users):
    if len(other_users) == 0:
        print("User {0} got matched with noone. This shouldn't have happened.".format(
            slack_user.roulette_user.name))
        return
    other_user_names = [user.name for user in other_users]
    message = "As a result of roulette #{0}, you got matched with {1}. Please organize a meeting until {2}.".format(
        roulette.pk, " and ".join(other_user_names), timezone.localtime(roulette.coffee_deadline))
    post_im(slack_user, message)


@receiver(post_matching)
def broadcast_matching_results(sender, instance, groups, **kwargs):
    # When a matching is done, send IMs to affected users on Slack
    if not SlackRoulette.objects.filter(roulette=instance).exists():
        return  # A roulette without Slack Roulette - do nothing.
    not_notified_user_names = []
    error_details = []
    for _, group in groups.items():
        users = [RouletteUser.objects.get(pk=user_id) for user_id in group]
        for user in users:
            try:
                other_users = [u for u in users if u.id != user.id]
                slack_user = SlackUser.objects.get(user=user)
                notify_matching_result(
                    instance, slack_user, other_users)
            except SlackUser.DoesNotExist:
                # TODO: try to correllate user with slack by the email we have. Maybe he didn't vote, but the admin added him.
                not_notified_user_names.append(user.name)
                error_details.append(
                    "We don't know how to find user {0} on Slack.".format(user.name))
            except Exception as exception:
                not_notified_user_names.append(user.name)
                error_details.append(
                    "Error happened while sending a notification to {0}: {1}.".format(user.name, exception))
    if len(not_notified_user_names) + len(error_details) > 0:
        # Notify the admins about errors
        message = "While notifying users about roulette results, some errors happened.\n" \
            "These users weren't notified: {0}\n" \
            "Details:\n{1}".format(
                ", ".join(not_notified_user_names), "\n".join(error_details))
        post_im_to_all_admins(message)
    # TODO send a message to everyone, finalizing the thread
