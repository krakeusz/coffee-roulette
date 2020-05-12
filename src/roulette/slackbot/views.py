from django.conf import settings as django_settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import SlackAdminUser, SlackRoulette
from matcher.models import Vote, Roulette, RouletteUser
from .webapi import post_im, fetch_votes as fetch_votes_impl

def get_slack_channel_or_none():
    try:
        return django_settings.SLACK_CHANNEL
    except:
        return None

def settings(request):
    slack_channel = get_slack_channel_or_none()
    return render(request, 'slackbot/settings.html', {'slack_channel' : slack_channel})

@require_POST
def send_hello_to_admins(request):
    users = SlackAdminUser.objects.all()
    if len(users) == 0:
        return HttpResponseRedirect(reverse('slackbot:no_admins'))
    for user in users:
        post_im(user, "Hi! This is a test message sent from the Coffee Roulette Django backend.")
    return HttpResponseRedirect(reverse('slackbot:message_sent'))

def message_sent(request):
    return render(request, 'slackbot/message_sent.html')

def no_admins(request):
    return render(request, 'slackbot/no_admins.html', {'user': request.user})

@require_POST
def fetch_votes(request, roulette_id):
    failure_type = 'unknown'
    try:
        slack_roulette = SlackRoulette.objects.filter(roulette=roulette_id).get()
        vote_list = fetch_votes_impl(slack_roulette)
        request.session['slackbot_vote_list'] = vote_list
        return HttpResponseRedirect(reverse('slackbot:fetch_votes_success', args=[roulette_id]))
    except SlackRoulette.DoesNotExist:
        failure_type = 'no_slack_thread'
    except:
        pass
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
    SlackRoulette.objects.filter(roulette=roulette_id).update(latest_response_timestamp=vote_list["last_message_timestamp"])
    return render(request, 'slackbot/fetch_votes/success.html', {'roulette_id': roulette_id, 'vote_list': vote_list})

def fetch_votes_failure(request, roulette_id, failure_type):
    return render(request, 'slackbot/fetch_votes/failure.html', {'roulette_id': roulette_id, 'failure_type': failure_type})
    


