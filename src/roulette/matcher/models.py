from datetime import timedelta
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class RouletteUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class Roulette(models.Model):
    vote_deadline = models.DateTimeField()
    coffee_deadline = models.DateTimeField()
    matchings_found_on = models.DateTimeField(null=True, default=None, )

    def __str__(self):
        return "Roulette with coffee deadline " + str(timezone.localtime(self.coffee_deadline))

    def clean(self):
        if self.vote_deadline >= self.coffee_deadline:
            raise ValidationError(
                "Coffee deadline must be set after vote deadline")

    def canAdminChangeVotes(self):
        return self.matchings_found_on is None

    def canAdminGenerateMatches(self):
        now = timezone.now()
        return now > self.vote_deadline and self.matchings_found_on is None

    def participatingUsers(self):
        users = []
        for yes_vote in self.vote_set.filter(choice='Y').select_related('user'):
            users.append(yes_vote.user)
        return users

    def getShortState(self):
        now = timezone.now()
        if now < self.vote_deadline:
            return "VOTING"
        elif self.matchings_found_on is None:
            return "MATCH NOW"
        elif now < self.coffee_deadline:
            return "COFFEE"
        else:
            return "FINISHED"

    def getPrettyState(self):
        now = timezone.now()
        if now < self.vote_deadline:
            return "Voting is active. The users can vote if they want to participate in this roulette. " \
                "The voting will end on " + \
                str(timezone.localtime(self.vote_deadline)) + "."
        elif self.matchings_found_on is None:
            return "Voting has ended. Please generate matchings now. " \
                "Coffee deadline is on " + \
                str(timezone.localtime(self.coffee_deadline)) + "."
        elif now < self.coffee_deadline:
            return "Matching has been done. Now it's the time for the users to meet. " \
                "Coffee deadline is on " + \
                str(timezone.localtime(self.coffee_deadline)) + "."
        else:
            return "This coffee roulette has ended on " + str(timezone.localtime(self.coffee_deadline)) + "."

    def __timediff__(self, diff):
        if diff.days == 0:
            if diff.seconds < 60:
                return "less than a minute"
            elif diff.seconds < 120:
                return "1 minute"
            elif diff.seconds < 3600:
                return "{0} minutes".format((diff.seconds // 60) % 60)
            else:
                return "{0} hour(s) {1} minute(s)".format(diff.seconds // 3600, (diff.seconds // 60) % 60)
        elif diff.days <= 1:
            return "1 day"
        elif diff.days <= 365:
            return "{0} days".format(diff.days)
        else:
            return "{0} year(s) {1} day(s)".format(diff.days // 365, diff.days % 365)

    def getRemainingString(self):
        now = timezone.now()
        if now < self.vote_deadline:
            return self.__timediff__(self.vote_deadline - now) + " until voting ends"
        elif now < self.coffee_deadline:
            return self.__timediff__(self.coffee_deadline - now) + " until coffee ends"
        else:
            return "coffee ended " + self.__timediff__(now - self.coffee_deadline) + " ago"


class Vote(models.Model):
    roulette = models.ForeignKey(Roulette, on_delete=models.CASCADE)
    user = models.ForeignKey(RouletteUser, on_delete=models.CASCADE)

    YES = 'Y'
    NO = 'N'
    NO_CHOICE_YET = '0'
    VOTE_CHOICES = [
        (YES, 'Yes'),
        (NO, 'No'),
        (NO_CHOICE_YET, 'No vote'),
    ]
    choice = models.CharField(
        max_length=3, choices=VOTE_CHOICES, default=NO_CHOICE_YET)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['roulette', 'user'], name='unique_vote')
        ]

    def pretty_choice(self):
        for choice_str, choice_verbose in self.VOTE_CHOICES:
            if self.choice == choice_str:
                return choice_verbose
        return 'Invalid vote'

    def __str__(self):
        return "Vote of {0} on {1}".format(self.user, self.pretty_choice())


class Match(models.Model):
    user_a = models.ForeignKey(
        RouletteUser, on_delete=models.CASCADE, related_name='+')
    user_b = models.ForeignKey(
        RouletteUser, on_delete=models.CASCADE, related_name='+')
    roulette = models.ForeignKey(Roulette, on_delete=models.CASCADE)

    def __str__(self):
        return "Match of " + str(self.user_a) + " with " + str(self.user_b) + " on " + str(self.roulette)


class ExclusionGroup(models.Model):
    users = models.ManyToManyField(RouletteUser)
    custom_name = models.CharField(
        max_length=128, blank=True, help_text="If left empty, it will be automatically generated.")

    def __str__(self):
        if self.custom_name == "":
            users = self.users.order_by('name').all()
            if len(users) == 0:
                return "Empty exclusion group"
            return ", ".join([user.name for user in users])
        return self.custom_name


class PenaltyGroup(models.Model):
    users = models.ManyToManyField(RouletteUser)
    custom_name = models.CharField(
        max_length=128, blank=True, help_text="If left empty, it will be automatically generated.")

    def __str__(self):
        if self.custom_name == "":
            users = self.users.order_by('name').all()
            if len(users) == 0:
                return "Empty penalty group"
            return ", ".join([user.name for user in users])
        return self.custom_name


class SingletonModel(models.Model):
    """ Singleton Django Model """
    """ Credit goes to https://stackoverflow.com/a/49736970 """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Save object to the database. Removes all other entries if there
        are any.
        """
        self.__class__.objects.exclude(id=self.id).delete()
        super(SingletonModel, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Load object from the database. Failing that, create a new empty
        (default) instance of the object and return it (without saving it
        to the database).
        """

        try:
            return cls.objects.get()
        except cls.DoesNotExist:
            return cls()

    def __str__(self):
        return "singleton object"


class PenaltyForRecentMatch(SingletonModel):
    penalty = models.FloatField(default=1.0)


class PenaltyForNumberOfMatches(SingletonModel):
    penalty = models.FloatField(default=0.5)


class PenaltyForPenaltyGroup(SingletonModel):
    penalty = models.FloatField(default=2.0)


class PenaltyForGroupingWithForbiddenUser(SingletonModel):
    penalty = models.FloatField(default=10.0)


def get_last_roulette():
    """ Returns either the last Roulette (by matching date) or None if there aren't any. """
    return Roulette.objects.exclude(matchings_found_on=None).order_by("-matchings_found_on").first()


def matching_graph(users):
    """ Returns [(user1, [(user2, weight), ...]), ...] """
    graph = []
    penalty_for_penalty_group = PenaltyForPenaltyGroup.objects.get_or_create()[
        0].penalty
    penalty_for_number_matches = PenaltyForNumberOfMatches.objects.get_or_create()[
        0].penalty
    penalty_for_recent_match = PenaltyForRecentMatch.objects.get_or_create()[
        0].penalty

    now = timezone.now()
    for user in users:
        user_ids_excluded = set()
        user_ids_excluded.add(user.id)
        # Exclude users from exclusion groups
        groups = ExclusionGroup.objects.filter(users__id=user.id).all()
        for group in groups:
            for excluded_user in RouletteUser.objects.filter(exclusiongroup__id=group.id):
                user_ids_excluded.add(excluded_user.id)
        # Exclude pairs generated in last run
        last_roulette = get_last_roulette()
        if last_roulette is not None:
            for match in last_roulette.match_set.all():
                if match.user_a.id == user.id:
                    user_ids_excluded.add(match.user_b.id)
                if match.user_b.id == user.id:
                    user_ids_excluded.add(match.user_a.id)
        edges = []
        for user2 in users:
            # Add edges
            if user2.id in user_ids_excluded:
                continue
            penalty = 0.0
            # And calculate the weights for them - penalty for penalty group
            groups_user2 = PenaltyGroup.objects.filter(
                users__id=user2.id).all()
            for group in groups_user2:
                if RouletteUser.objects.filter(penaltygroup__id=group.id).filter(id=user.id).exists():
                    penalty += penalty_for_penalty_group
            # Penalty for number of matches
            user_user2_matches = Match.objects.filter(
                Q(user_a=user, user_b=user2) | Q(user_a=user2, user_b=user))
            penalty += len(user_user2_matches) * penalty_for_number_matches
            # Penalties for recent matches
            recent_user_user2_matches = user_user2_matches.filter(
                roulette__matchings_found_on__gte=now - timedelta(days=365)).all()
            for match in recent_user_user2_matches:
                time_passed = now - match.roulette.matchings_found_on
                days_passed = time_passed.days
                penalty += max(0.0, penalty_for_recent_match *
                               (1.0 - days_passed / 365.0))  # linear relationship
            edges.append((user2, penalty))

        graph.append((user, edges))
    return graph
