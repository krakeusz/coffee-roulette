from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import SlackAdminUser
from .webapi import postIM

def get_slack_channel_or_none():
    try:
        return settings.SLACK_CHANNEL
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
        postIM(user, "Hi! This is a test message sent from the Coffee Roulette Django backend.")
    return HttpResponseRedirect(reverse('slackbot:message_sent'))

def message_sent(request):
    return render(request, 'slackbot/message_sent.html')

def no_admins(request):
    return render(request, 'slackbot/no_admins.html', {'user': request.user})


