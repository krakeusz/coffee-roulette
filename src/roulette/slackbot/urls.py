from django.urls import path
from . import views

app_name = 'slackbot'
urlpatterns = [
    path('configuration', views.configuration, name='configuration'),
    path('send_message', views.send_message, name='send_message'),
    path('message_sent', views.message_sent, name='message_sent'),
]