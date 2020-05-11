import slack

from django.conf import settings
from .models import SlackAdminUser

def create_web_client():
    return slack.WebClient(token=settings.SLACK_BOT_TOKEN)

def open_im_channel_if_not_opened(slack_user):
    """
    Opens a new direct channel between slackbot and slack_user, if it hasn't been done yet.
    slack_user can be either a SlackUser or SlackAdminUser instance.
    Returns the string identifying new channel.
    """
    if len(slack_user.im_channel) == 0:
        response = create_web_client().conversations_open(users=str(slack_user.slack_user_id))
        if not response["ok"]:
            raise Exception("Could not open Slack private conversation channel with user {0}: {1}".format(slack_user.slack_user_id, response["error"]))
        slack_user.im_channel = response["channel"]["id"]
        slack_user.save()
    return slack_user.im_channel

def post_im(slack_user, text):
    """ Send an instant message to one slack user.
    slack_user can be either a SlackUser or SlackAdminUser instance.
    Returns nothing, throws on error.
    """
    channel = open_im_channel_if_not_opened(slack_user)
    response = create_web_client().chat_postMessage(channel=channel, text=text)
    if not response["ok"]:
        raise Exception("Could not send Slack IM message to user {0}: {1}".format(slack_user.slack_user.id, response["error"]))

def post_im_to_all_admins(text):
    """ Send an instant message to all slack admins on Slack.
    Throws on error. """
    for admin in SlackAdminUser.objects.all():
        post_im(admin, text)

def post_on_channel(channel, text):
    """
    Send a message on public or private group channel.
    channel can be either #channel-name or slack channel ID.
    If sending succeeds, returns timestamp of the new thread, for future correlation.
    Throws on error.
    """
    response = create_web_client().chat_postMessage(channel=channel, text=text)
    if not response["ok"]:
        raise Exception("Could not send Slack message on channel {0}: {1}".format(channel, response["error"]))
    return response["ts"]

def post_on_thread(channel, thread_timestamp, text):
    """
    Send a message on given thread (probably part of a channel).
    channel can be either #channel-name or slack channel ID.
    If sending succeeds, returns timestamp of the new message.
    Throws on error.
    """
    response = create_web_client().chat_postMessage(channel=channel, thread_ts=thread_timestamp, text=text)
    if not response["ok"]:
        raise Exception("Could not send Slack message on channel {0}, thread {1}: {2}".format(channel, thread_timestamp, response["error"]))
    return response["ts"]