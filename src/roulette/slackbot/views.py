from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .exceptions import NoWorkspaceError
from .models import SlackAdminUser, SlackRoulette, SlackWorkspace
from matcher.models import Vote, Roulette, RouletteUser
from .webapi import BotClient


def settings(request):
    slack_workspace = None
    if SlackWorkspace.objects.exists():
        slack_workspace = SlackWorkspace.objects.get()
    return render(request, 'slackbot/settings.html', {'slack_workspace': slack_workspace})


@require_POST
def send_hello_to_admins(request):
    try:
        users = SlackAdminUser.objects.all()
        if len(users) == 0:
            return HttpResponseRedirect(reverse('slackbot:send_message_failure'), args=['no_admins'])
        client = BotClient()
        for user in users:
            client.post_im(
                user, "Hi! This is a test message sent from the Coffee Roulette Django backend.")
        return HttpResponseRedirect(reverse('slackbot:send_message_success'))
    except NoWorkspaceError:
        return HttpResponseRedirect(reverse('slackbot:send_message_failure'), args=['no_slack_workspace'])


def send_message_success(request):
    return render(request, 'slackbot/send_message/success.html')


def send_message_failure(request, failure_type):
    return render(request, 'slackbot/send_message/failure.html', {'user': request.user, 'failure_type': failure_type})


@require_POST
def fetch_votes(request, roulette_id):
    failure_type = 'unknown'
    try:
        roulette = Roulette.objects.get(pk=int(roulette_id))
        if not roulette.canVotesBeChanged():
            failure_type = 'too_late_for_changing_votes'
            raise Exception()
        slack_roulette = SlackRoulette.objects.get(roulette=int(roulette_id))
        vote_list = BotClient().fetch_votes(slack_roulette)
        request.session['slackbot_vote_list'] = vote_list
        return HttpResponseRedirect(reverse('slackbot:fetch_votes_success', args=[roulette_id]))
    except SlackRoulette.DoesNotExist:
        failure_type = 'no_slack_thread'
    except NoWorkspaceError:
        failure_type = 'no_slack_workspace'
    except Exception as exception:
        print(exception)
    return HttpResponseRedirect(reverse('slackbot:fetch_votes_failure', args=[roulette_id, failure_type]))


def fetch_votes_success(request, roulette_id):
    vote_list = request.session.get('slackbot_vote_list', None)
    if vote_list is None:
        return HttpResponseRedirect(reverse('slackbot:fetch_votes_failure', args=[roulette_id, 'no_vote_list']))
    del request.session['slackbot_vote_list']
    vote_instances = []
    for vote_dict in vote_list["votes"]:
        vote, _ = Vote.objects.update_or_create(
            roulette=int(vote_dict["roulette_id"]),
            user=int(vote_dict["roulette_user_id"]),
            defaults={"choice": vote_dict["choice"]}
        )
        vote_instances.append(vote)
    vote_list["votes"] = vote_instances
    SlackRoulette.objects.filter(roulette=roulette_id).update(
        latest_response_timestamp=vote_list["last_message_timestamp"])
    return render(request, 'slackbot/fetch_votes/success.html', {'roulette_id': roulette_id, 'vote_list': vote_list})


def fetch_votes_failure(request, roulette_id, failure_type):
    return render(request, 'slackbot/fetch_votes/failure.html', {'roulette_id': roulette_id, 'failure_type': failure_type})
