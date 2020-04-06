
from django.conf import settings
from django.core.management.base import BaseCommand
import asyncio
import certifi
import slack
import ssl as ssl_lib
import time

def get_user_mention_block(sender_username):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "User {0} wrote this:".format(sender_username)
            ),
        },
    }

DIVIDER_BLOCK = {"type": "divider"}

def get_user_reply_block(text):
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                text
            ),
        },
    }

def get_reply_payload(channel, sender_username, text):
        return {
            "ts": "",
            "channel": channel,
            "username": settings.SLACK_BOT_VISIBLE_NAME,
            "icon_emoji": settings.SLACK_BOT_ICON_EMOJI,
            "blocks": [
                get_user_mention_block(sender_username),
                DIVIDER_BLOCK,
                get_user_reply_block(text),
                DIVIDER_BLOCK,
            ],
        }

# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@slack.RTMClient.run_on(event="message")
async def message(**payload):
    """Log all messages to stdout.
    """
    data = payload["data"]
    # Get WebClient so you can communicate back to Slack.
    web_client = payload["web_client"]
    channel_id = data.get("channel")
    user_id = data.get("user")
    text = data.get("text")
    if user_id is None:
        return
    print("Message received from user {0} on channel {1}.\n{2}".format(user_id, channel_id, text))
    # Respond with the same message.
    reply = get_reply_payload(channel_id, user_id, text)
    response = await web_client.chat_postMessage(**reply)
    print("Reply sent, response was: {0}".format(response))

        
class Command(BaseCommand):
    help = 'Starts the bot to listen for Slack events'

    def handle(self, *args, **options):
        ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        rtm_client = slack.RTMClient(
            token=settings.SLACK_BOT_TOKEN, ssl=ssl_context, run_async=True, loop=loop
        )
        loop.run_until_complete(rtm_client.start())