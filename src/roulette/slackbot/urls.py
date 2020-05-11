from django.urls import path
from . import views

app_name = 'slackbot'
urlpatterns = [
    path('configuration', views.configuration, name='configuration'),
    path('send_message', views.send_hello_to_admins, name='send_message'),
    path('message_sent', views.message_sent, name='message_sent'),
    path('no_admins', views.no_admins, name='no_admins'),
]