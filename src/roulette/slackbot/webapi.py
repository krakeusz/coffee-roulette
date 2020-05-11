import slack

from django.conf import settings

def createWebClient():
    return slack.WebClient(token=settings.SLACK_BOT_TOKEN)

def openIMChannelIfNotOpened(slack_user):
    """
    Opens a new direct channel between slackbot and slack_user, if it hasn't been done yet.
    slack_user can be either a SlackUser or SlackAdminUser instance.
    Returns the string identifying new channel.
    """
    if len(slack_user.im_channel) == 0:
        response = createWebClient().conversations_open(users=str(slack_user.slack_user_id))
        if not response["ok"]:
            raise Exception("Could not open Slack private conversation channel with user {0}: {1}".format(slack_user.slack_user_id, response["error"]))
        slack_user.im_channel = response["channel"]["id"]
        slack_user.save()
    return slack_user.im_channel

def postIM(slack_user, text):
    channel = openIMChannelIfNotOpened(slack_user)
    response = createWebClient().chat_postMessage(channel=channel, text=text)
    if not response["ok"]:
        raise Exception("Could not send Slack IM message to user {0}: {1}".format(slack_user.slack_user.id, response["error"]))