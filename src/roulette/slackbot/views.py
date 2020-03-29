from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.urls import reverse

from django_slack import slack_message


def configuration(request):
    return render(request, 'slackbot/configuration.html', {})

@require_POST
def send_message(request):
    slack_message('slackbot/test_message.slack', {})
    return HttpResponseRedirect(reverse('slackbot:message_sent'))

def message_sent(request):
    return render(request, 'slackbot/message_sent.html')
