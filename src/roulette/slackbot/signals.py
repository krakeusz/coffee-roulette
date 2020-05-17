from django.db.models.signals import post_save
from django.dispatch import receiver
from matcher.models import Roulette, RouletteUser
from matcher.signals import post_matching
from .models import SlackRoulette, SlackUser
from .webapi import corellate_slack_user_by_email, post_on_channel, post_on_thread, post_im_to_all_admins, post_im
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


def _notify_matching_result_(roulette, slack_user, other_users):
    if len(other_users) == 0:
        print("User {0} got matched with noone. This shouldn't have happened.".format(
            slack_user.roulette_user.name))
        return
    other_user_names = [user.name for user in other_users]
    message = "As a result of roulette #{0}, you got matched with {1}. Please organize a meeting until {2}.".format(
        roulette.pk, " and ".join(other_user_names), timezone.localtime(roulette.coffee_deadline))
    post_im(slack_user, message)


def _notify_all_matching_results_(roulette, groups):
    """
    Try to notify all users participating in roulette about matching results.
    'roulette' is the Roulette instance.
    'groups' is a dict of group_id => list of user ids that belong to the group. str => list(int)
    Return a list of pairs, (not_notified_user_name, error_detail_string).
    """
    errors = []
    for _, group in groups.items():
        users = [RouletteUser.objects.get(pk=user_id) for user_id in group]
        for user in users:
            try:
                other_users = [u for u in users if u.id != user.id]
                if not SlackUser.objects.filter(user=user).exists():
                    corellate_slack_user_by_email(user)
                slack_user = SlackUser.objects.get(user=user)
                _notify_matching_result_(
                    roulette, slack_user, other_users)
            except SlackUser.DoesNotExist:
                errors.append(
                    (user.name, "User {0} could not be found on Slack. His email {1} is not tied to his/her Slack account".format(user.name, user.email)))
            except Exception as exception:
                errors.append((user.name, "Error happened while sending a notification to {0}: {1}.".format(
                    user.name, exception)))
    return errors


def _post_matching_summary_(roulette, groups):
    """
    Send a final message on the roulette thread, telling that the matching is done.
    """
    try:
        user_count = sum([len(group) for group in groups.values()])
        message = "Thank you for your votes. A total of {0} user(s) are going to meet.\n" \
            "If you participate, you will get a personal message with your match soon.".format(
                user_count)
        slack_roulette = SlackRoulette.objects.get(roulette=roulette)
        post_on_thread(slack_roulette.channel_id,
                       slack_roulette.thread_timestamp, message)
    except Exception as exception:
        return [(None, "Could not post public matching summary: {0}".format(exception))]
    return []


def _notify_admins_about_errors_(errors):
    if len(errors) > 0:
        # Notify the admins about errors
        not_notified_user_names, error_details = tuple(zip(*errors))
        not_notified_user_names = [
            user_name for user_name in not_notified_user_names if user_name is not None]
        message = "While notifying users about roulette results, some errors happened.\n" \
            "These users weren't notified: {0}\n" \
            "Details:\n{1}".format(
                ", ".join(not_notified_user_names), "\n".join(error_details))
        post_im_to_all_admins(message)


@receiver(post_matching)
def broadcast_matching_results(sender, instance, groups, **kwargs):
    # When a matching is done, send IMs to affected users on Slack
    if not SlackRoulette.objects.filter(roulette=instance).exists():
        return  # A roulette without Slack Roulette - do nothing.
    errors = _notify_all_matching_results_(instance, groups)
    errors.extend(_post_matching_summary_(instance, groups))
    _notify_admins_about_errors_(errors)
