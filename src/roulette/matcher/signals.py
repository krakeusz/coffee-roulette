from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from .models import Roulette, RouletteUser, Vote

# post_matching is sent when a matching completes successfully.
# 'sender' will be the Roulette class.
# 'instance' will be the Roulette instance that matching is tied to.
# 'groups' will be dict of group_id => list of user ids that belong to the group. str => list(int)
post_matching = Signal(providing_args=["instance", "groups"])


@receiver(post_save, sender=Roulette)
def add_default_votes(sender, instance, created, **kwargs):
    # When roulette is saved for the first time, add default (empty) votes
    roulette = instance
    if created and len(roulette.vote_set.all()) == 0:
        for user in RouletteUser.objects.all():
            Vote.objects.create(roulette=roulette, user=user)


@receiver(post_save, sender=RouletteUser)
def add_user_to_active_roulettes(sender, instance, created, **kwargs):
    # When a user is created, add default votes for active roulettes
    if not created:
        return
    active_roulettes = Roulette.objects.filter(
        matchings_found_on=None).filter()
    for roulette in active_roulettes:
        if not Vote.objects.filter(roulette=roulette).filter(user=instance).exists():
            Vote.objects.create(roulette=roulette, user=instance)
