from django.db import models
from matcher.models import RouletteUser

class SlackUser(models.Model):
    """ Extends the RouletteUser model with Slack user id field.
        This field can be queried from Slack API, for example if we know user's email.
        The idea is that by default a RouletteUser exists without assigned SlackUser,
        but when the SlackUser could be used, it will be created by reading user list from Slack.
    """
    roulette_user = models.OneToOneField(RouletteUser, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=20)

    def __str__(self):
        return str(self.roulette_user)
