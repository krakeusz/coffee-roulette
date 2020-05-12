from django.urls import path
from . import views

app_name = 'slackbot'
urlpatterns = [
    path('settings', views.settings, name='settings'),
    path('send_message', views.send_hello_to_admins, name='send_message'),
    path('message_sent', views.message_sent, name='message_sent'),
    path('no_admins', views.no_admins, name='no_admins'),
    path('fetch_votes/<int:roulette_id>/',
         views.fetch_votes, name='fetch_votes'),
    path('fetch_votes/<int:roulette_id>/success/',
         views.fetch_votes_success, name='fetch_votes_success'),
    path('fetch_votes/<int:roulette_id>/failure/<slug:failure_type>',
         views.fetch_votes_failure, name='fetch_votes_failure'),
]
