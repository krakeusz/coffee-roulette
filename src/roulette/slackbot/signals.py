from django.db.models.signals import post_save
from django.dispatch import receiver
from matcher.models import Roulette
from .models import SlackRoulette
from .webapi import post_on_channel, post_on_thread, post_im_to_all_admins
from django.conf import settings
from django.utils import timezone

@receiver(post_save, sender=Roulette)
def broadcast_new_roulette(sender, instance, created, **kwargs):
    # When a roulette is created, create a new thread on Slack
    if not created:
        return
    try:
        thread_ts = post_on_channel(settings.SLACK_CHANNEL, (
            "A new coffee roulette #{0} is going to start!"
            " If you want to participate, please reply in this thread.\n"
            "The voting deadline is {1}. Coffee will end on {2}\n"
            ).format(instance.pk, timezone.localtime(instance.vote_deadline), timezone.localtime(instance.coffee_deadline)))
        first_reply_ts = post_on_thread(settings.SLACK_CHANNEL, thread_ts, "Please vote by writing YES or NO. If you don't vote, you won't participate.")

    except Exception as exception:
        print(str(exception))
        try:
            post_im_to_all_admins("While saving the roulette #{0}, an error occured."
                                  " Consider fixing the issue and deleting the faulty roulette."
                                  " Error was:\n{1}".format(instance.pk, str(exception)))
        except Exception as nestedException:
            print(str(nestedException))
        return

    SlackRoulette.objects.create(roulette = instance, thread_timestamp = thread_ts, latest_response_timestamp = first_reply_ts)

