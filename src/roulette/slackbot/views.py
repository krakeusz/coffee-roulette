from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.urls import reverse

from .models import SlackAdminUser
from .webapi import postIM


def configuration(request):
    return render(request, 'slackbot/configuration.html', {})

@require_POST
def send_message(request):
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


