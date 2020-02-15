from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

class RouletteUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    
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
            raise ValidationError("Coffee deadline must be set after vote deadline")

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

    def getPrettyState(self):
        now = timezone.now()
        if now < self.vote_deadline:
            return "Voting is active. The users can vote if they want to participate in this roulette. " \
                "The voting will end on " + str(timezone.localtime(self.vote_deadline)) + "."
        elif self.matchings_found_on is None:
            return "Voting has ended. Please generate matchings now. " \
                "Coffee deadline is on " + str(timezone.localtime(self.coffee_deadline)) + ". Please note that the system doesn't care when or whether the users meet."
        elif now < self.coffee_deadline:
            return "Matching has been done. Now it's the time for the users to meet. " \
                "Coffee deadline is on " + str(timezone.localtime(self.coffee_deadline)) + ". Please note that the system doesn't care when or whether the users meet."
        else:
            return "This coffee roulette has ended on " + str(timezone.localtime(self.coffee_deadline)) + "."

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
    choice = models.CharField(max_length=3, choices=VOTE_CHOICES, default=NO_CHOICE_YET)

    def __str__(self):
        return "Vote of " + str(self.user) + " on " + str(self.roulette)

class Match(models.Model):
    user_a = models.ForeignKey(RouletteUser, on_delete=models.CASCADE, related_name='+')
    user_b = models.ForeignKey(RouletteUser, on_delete=models.CASCADE, related_name='+')
    roulette = models.ForeignKey(Roulette, on_delete=models.CASCADE)
    
    def __str__(self):
        return "Match of " + str(self.user_a) + " with " + str(self.user_b) + " on " + str(self.roulette)

class ExclusionGroup(models.Model):
    users = models.ManyToManyField(RouletteUser)
    custom_name = models.CharField(max_length=128, blank=True, help_text="If left empty, it will be automatically generated.")

    def __str__(self):
        if self.custom_name == "":
            users = self.users.order_by('name').all()
            if len(users) == 0:
                return "Empty exclusion group"
            return ", ".join([user.name for user in users])
        return self.custom_name


class PenaltyGroup(models.Model):
    users = models.ManyToManyField(RouletteUser)
    custom_name = models.CharField(max_length=128, blank=True, help_text="If left empty, it will be automatically generated.")

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
    (penalty_for_penalty_group, _) = PenaltyForPenaltyGroup.objects.get_or_create()
    penalty_for_penalty_group = penalty_for_penalty_group.penalty
    for user in users:
        user_ids_excluded = set()
        user_ids_excluded.add(user.id)
        # Exclude users from exclusion groups
        groups = ExclusionGroup.objects.filter(users__id = user.id).all()
        for group in groups:
            for excluded_user in RouletteUser.objects.filter(exclusiongroup__id = group.id):
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
        user_matches = Match.objects.filter(Q(user_a=user) | Q(user_b=user)).all()
        for user2 in users:
            # Add edges
            if user2.id in user_ids_excluded:
                continue
            penalty = 0.0
            # And calculate the weights for them - penalty for penalty group
            groups_user2 = PenaltyGroup.objects.filter(users__id = user2.id).all()
            for group in groups_user2:
                if RouletteUser.objects.filter(penaltygroup__id = group.id).filter(id=user.id).exists():
                    penalty += penalty_for_penalty_group
            # Penalty for number of matches
            #TODO
            edges.append((user2, penalty))
        # TODO: add penalties for recent matches
        # TODO: add penalties for number of matches

        graph.append((user, edges))
    return graph
