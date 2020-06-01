from django.contrib import auth
from django.db import models
from matcher.models import Roulette, RouletteUser


class AtMostOneInstanceModel(models.Model):
    """ A Model that can have only one instance in database. """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Save object to the database. Removes all other entries if there
        are any.
        """
        self.__class__.objects.exclude(id=self.id).delete()
        super(AtMostOneInstanceModel, self).save(*args, **kwargs)


class SlackWorkspace(AtMostOneInstanceModel):
    """
    Provides constants required for communication with Slack workspace.
    There can be only one instance in database. We don't support multiple workspaces.
    """
    roulette_channel = models.CharField(
        max_length=255, help_text="Name of the Slack channel that the bot will post public messages on. Starts with #.")
    bot_api_token = models.CharField(
        max_length=255, help_text="A secret token that allows using Slack Web API, tied to a Slack app installation.")


class SlackUser(models.Model):
    """ Extends the RouletteUser model with Slack user id field.
        This field can be queried from Slack API, for example if we know user's email.
        The idea is that by default a RouletteUser exists without assigned SlackUser,
        but if the user interacts on Slack, or we need to send him a Slack message, a SlackUser instance is created.
    """
    # user The required connection to the Roulette user model.
    user = models.OneToOneField(RouletteUser, on_delete=models.CASCADE)
    # slack_user_id The user ID assigned by Slack. Needed to send IMs to the user through Slack Web API, and to properly assign Slack messages to our RouletteUsers.
    slack_user_id = models.CharField(max_length=20, unique=True)
    # im_channel The ID of one-to-one message channel, opened when we send the first message to the user.
    im_channel = models.CharField(max_length=20, default="", blank=True)

    def __str__(self):
        return str(self.user)


class SlackAdminUser(models.Model):
    """ Extends the django.contrib.auth.User by providing Slack user ID.
        All SlackAdminUsers will be notified on Slack in case an error or warning happens.
        Being a SlackAdminUser does not imply being a SlackUser. If the admin want to take part in roulettes, he/she needs to create a RouletteUser.
    """
    user = models.OneToOneField(auth.models.User, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=20, unique=True)
    im_channel = models.CharField(max_length=20, default="", blank=True)

    def __str__(self):
        return str(self.user)


class SlackRoulette(models.Model):
    """ Extends the matcher.models.Roulette model with data needed for Slack interactions. """
    roulette = models.OneToOneField(Roulette, on_delete=models.CASCADE)
    thread_timestamp = models.CharField(max_length=30)
    latest_response_timestamp = models.CharField(max_length=30, default="0")
    channel_id = models.CharField(max_length=20)
