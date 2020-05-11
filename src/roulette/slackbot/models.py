from django.contrib import auth
from django.db import models
from matcher.models import Roulette, RouletteUser

class SlackUser(models.Model):
    """ Extends the RouletteUser model with Slack user id field.
        This field can be queried from Slack API, for example if we know user's email.
        The idea is that by default a RouletteUser exists without assigned SlackUser,
        but when the SlackUser could be used, it will be created by reading user list from Slack.
    """
    user = models.OneToOneField(RouletteUser, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=20)
    im_channel = models.CharField(max_length=20, default="", blank=True)

    def __str__(self):
        return str(self.user)

class SlackAdminUser(models.Model):
    """ Extends the django.contrib.auth.User by providing Slack user ID.
        All SlackAdminUsers will be notified on Slack in case an error or warning happens.
    """
    user = models.OneToOneField(auth.models.User, on_delete=models.CASCADE)
    slack_user_id = models.CharField(max_length=20)
    im_channel = models.CharField(max_length=20, default="", blank=True)

    def __str__(self):
        return str(self.user)

class SlackRoulette(models.Model):
    """ Extends the matcher.models.Roulette model with data needed for Slack interactions. """
    roulette = models.OneToOneField(Roulette, on_delete=models.CASCADE)
    thread_timestamp = models.CharField(max_length=30)
    latest_response_timestamp = models.CharField(max_length=30, default="0")

# TODO needed?
class SingletonNoDefaultModel(models.Model):
    """ Singleton Django Model without default creation """
    """ Similar to matcher.models.SingletonModel, but doesn't create a default instance for the first time. """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Save object to the database. Removes all other entries if there
        are any.
        """
        self.__class__.objects.exclude(id=self.id).delete()
        super(SingletonNoDefaultModel, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        """
        Load object from the database. Failing that, return None.
        """
        try:
            return cls.objects.get()
        except cls.DoesNotExist:
            return None
    
    def __str__(self):
        return "singleton object"
