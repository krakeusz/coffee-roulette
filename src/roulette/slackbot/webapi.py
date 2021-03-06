import re
import slack

from django.conf import settings
from .exceptions import NoWorkspaceError, SlackbotError
from .models import SlackAdminUser, SlackUser, SlackWorkspace
from matcher.models import RouletteUser
from decimal import Decimal


class BotClient():
    """
    A class to use to interact with Slack.
    """
    _webclient = None
    _slack_workspace = None

    def __init__(self):
        try:
            self._slack_workspace = SlackWorkspace.objects.get()
            self._webclient = slack.WebClient(
                token=self._slack_workspace.bot_api_token)
        except SlackWorkspace.DoesNotExist:
            raise NoWorkspaceError()

    def _open_im_channel_if_not_opened(self, slack_user):
        """
        Opens a new direct channel between slackbot and slack_user, if it hasn't been done yet.
        slack_user can be either a SlackUser or SlackAdminUser instance.
        Returns the string identifying new channel.
        """
        if len(slack_user.im_channel) == 0:
            response = self._webclient.conversations_open(
                users=str(slack_user.slack_user_id))
            if not response["ok"]:
                raise SlackbotError("Could not open Slack private conversation channel with user {0}: {1}".format(
                    slack_user.slack_user_id, response["error"]))
            slack_user.im_channel = response["channel"]["id"]
            slack_user.save()
        return slack_user.im_channel

    def post_im(self, slack_user, text):
        """
        Send an instant message to one slack user.
        slack_user can be either a SlackUser or SlackAdminUser instance.
        Return nothing, throw on error.
        """
        channel = self._open_im_channel_if_not_opened(slack_user)
        response = self._webclient.chat_postMessage(channel=channel, text=text)
        if not response["ok"]:
            raise SlackbotError("Could not send Slack IM message to user {0}: {1}".format(
                slack_user.slack_user.id, response["error"]))

    def post_im_to_all_admins(self, text):
        """
        Send an instant message to all slack admins on Slack.
        Throw on error.
        """
        for admin in SlackAdminUser.objects.all():
            self.post_im(admin, text)

    def post_on_roulette_channel(self, text):
        """
        Send a message on channel configured by the admin.
        If sending succeeds, return pair (timestamp, channel_id).
        timestamp is the timestamp of the new thread, for future correlation.
        channel_id is the slack ID of the channel.
        Throw on error.
        """
        return self.post_on_channel(self._slack_workspace.roulette_channel, text)

    def post_on_channel(self, channel, text):
        """
        Send a message on public or private group channel.
        channel can be either #channel-name or slack channel ID.
        If sending succeeds, return pair (timestamp, channel_id).
        timestamp is the timestamp of the new thread, for future correlation.
        channel_id is the slack ID of the channel. This is an easy way to get channel ID from channel name without requiring too many bot permissions.
        Throw on error.
        """
        response = self._webclient.chat_postMessage(channel=channel, text=text)
        if not response["ok"]:
            raise SlackbotError("Could not send Slack message on channel {0}: {1}".format(
                channel, response["error"]))
        return (response["ts"], response["channel"])

    def post_on_thread(self, channel, thread_timestamp, text):
        """
        Send a message on given thread (probably part of a channel).
        channel can be either #channel-name or slack channel ID.
        If sending succeeds, return timestamp of the new message.
        Throw on error.
        """
        response = self._webclient.chat_postMessage(
            channel=channel, thread_ts=thread_timestamp, text=text)
        if not response["ok"]:
            raise SlackbotError("Could not send Slack message on channel {0}, thread {1}: {2}".format(
                channel, thread_timestamp, response["error"]))
        return response["ts"]

    def _slack_user_to_dict(self, slack_user):
        """
        Converts a slackbot.models.SlackUser instance to a dictionary, as used by get_or_corellate_slack_user.
        """
        return {
            "slack_id": slack_user.slack_user_id,
            "database_slack_user_id": str(slack_user.pk),
            "display_name": slack_user.user.name,
            "real_name": None,
            "email": slack_user.user.email
        }

    def get_or_corellate_slack_user(self, slack_user_id):
        """
        Find or create a SlackUser instance, searching by slack_user_id or linked RouletteUser's email.
        If the SlackUser doesn't exist, but the email of user slack_user_id as returned by Slack API is in our database,
        then create a new SlackUser instance in database.
        Return a dictionary, for example:
        {
            "slack_id": "U12345",
            "database_slack_user_id": None,
            "display_name": "johnny",
            "real_name": "John Smith",
            "email": "john.smith.slack.alias@example.com"
        }
        If database_slack_user_id is not None, then the returned instance corresponds to a SlackUser object.
        """
        slack_users_by_id = SlackUser.objects.filter(
            slack_user_id=slack_user_id)
        if len(slack_users_by_id) > 0:
            return self._slack_user_to_dict(slack_users_by_id.get())

        # Corellate user account on Slack with SlackUser by his/her email address, which both we and Slack require.
        response = self._webclient.users_info(user=slack_user_id)
        if not response["ok"]:
            raise SlackbotError("Could not fetch email of user {0}: {1}".format(
                slack_user_id, response["error"]))
        profile = response["user"]["profile"]
        email = profile.get("email")
        roulette_users_by_email = RouletteUser.objects.filter(email=email)
        if len(roulette_users_by_email) == 0:
            return {
                "slack_id": slack_user_id,
                "database_slack_user_id": None,
                "display_name": profile.get("display_name"),
                "real_name": profile.get("real_name"),
                "email": email
            }
        roulette_user = roulette_users_by_email.get()
        slack_user = SlackUser.objects.create(
            user=roulette_user, slack_user_id=slack_user_id)
        return self._slack_user_to_dict(slack_user)

    def corellate_slack_user_by_email(self, roulette_user):
        """
        Find a user on Slack given the email field in RouletteUser parameter.
        If this succeeds, create and return a SlackUser instance.
        Raise a SlackbotError if there was no such Slack user or the Slack Web API returns an error.
        """
        response = self._webclient.users_lookupByEmail(
            email=roulette_user.email)
        if not response["ok"]:
            # TODO it seems that we can't enter this branch because, on error, slack client throws an exception by itself.
            # After writing tests, try to remove all bad response handling code from this file.
            raise SlackbotError("Could not find Slack user by email {0}: {1}".format(
                roulette_user.email, response["error"]))
        return SlackUser.objects.create(user=roulette_user, slack_user_id=response["user"]["id"])

    def _parse_vote(self, message_text, slack_user, roulette):
        """
        Try to parse user's message, which is supposed to be a vote.
        Return a dictionary, for example:
        {
            "choice": "Y",
            "roulette_id": "45",
            "roulette_user_id": "32"
        }, or None if the parsing failed.
        """
        stripped_message = re.sub('[ \t\n\r.!]', '', message_text).lower()
        vote = {"roulette_id": str(roulette.id),
                "roulette_user_id": str(slack_user.user.id)}
        if stripped_message == "yes":
            vote["choice"] = "Y"
        elif stripped_message == "no":
            vote["choice"] = "N"
        else:
            return None
        return vote

    def fetch_votes(self, slack_roulette):
        """
        Parse the messages on the Slack thread which is connected to the roulette.
        Look only at the messages that have appeared since the last call of this function.
        As a side effect, this function may save new slackbot.models.SlackUser objects into database,
        if a correlation between matcher.models.RouletteUser.email and official Slack profile's email is found.
        sample_result = {
            "last_message_timestamp": "1503435956.000247",
            "votes": [
                {
                    "choice": "Y",
                    "roulette_id": "45",
                    "roulette_user_id": "32"
                },
                {
                    "choice": "N",
                    "roulette_id": "45",
                    "roulette_user_id": "33"
                }
            ],
            "unknown_messages": [
                {
                    "user": {
                        "slack_id": "U12345",
                        "database_slack_user_id": None,
                        "display_name": "johnny",
                        "real_name": "John Smith",
                        "email": "john.smith.slack.alias@example.com"
                    },
                    "text": "YES",
                    "reason": "Could not correlate our data with Slack using email field."
                },
                {
                    "user": {
                        "slack_id": "U51342",
                        "database_slack_user_id": "12",
                        "display_name": "johnny",
                        "real_name": None,
                        "email": "john.smith.official@example.com"
                    },
                    "text": "YSE",
                    "reason": "Could not parse user's message."
                }
            ]
        }
        """
        vote_list = {
            "last_message_timestamp": slack_roulette.latest_response_timestamp,
            "votes": [],
            "unknown_messages": []
        }
        more = True
        reps_remaining = 100
        while more:
            response = self._webclient.conversations_replies(
                channel=slack_roulette.channel_id, ts=slack_roulette.thread_timestamp, oldest=vote_list["last_message_timestamp"])
            if not response["ok"]:
                raise SlackbotError("Could not fetch Slack thread replies on channel {0}, thread {1}: {2}".format(
                    slack_roulette.channel_id, slack_roulette.thread_timestamp, response["error"]))
            for message in response["messages"]:
                if message["ts"] == slack_roulette.thread_timestamp:
                    # Slack returns the thread parent message too. We ignore it.
                    continue
                user_dict = self.get_or_corellate_slack_user(message["user"])
                if user_dict["database_slack_user_id"] is None:
                    vote_list["unknown_messages"].append(
                        {"user": user_dict, "text": message["text"], "reason": "Could not correlate our data with Slack using email field."})
                else:
                    slack_user = SlackUser.objects.get(
                        pk=int(user_dict["database_slack_user_id"]))
                    vote = self._parse_vote(
                        message["text"], slack_user, slack_roulette.roulette)
                    if vote is None:
                        vote_list["unknown_messages"].append({"user": self._slack_user_to_dict(
                            slack_user), "text": message["text"], "reason": "Could not parse user's message."})
                    else:
                        vote_list["votes"].append(vote)
                if Decimal(message["ts"]) > Decimal(vote_list["last_message_timestamp"]):
                    vote_list["last_message_timestamp"] = message["ts"]
            more = response["has_more"]
            reps_remaining -= 1
            if reps_remaining <= 0:
                more = False
        return vote_list
