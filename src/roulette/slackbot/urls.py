from django.urls import path
from . import views

app_name = 'slackbot'
urlpatterns = [
    path('settings', views.settings, name='settings'),
    path('send_message', views.send_hello_to_admins, name='send_message'),
    path('send_message/success', views.send_message_success,
         name='send_message_success'),
    path('send_message/failure/<slug:failure_type>',
         views.send_message_failure, name='send_message_failure'),
    path('fetch_votes/<int:roulette_id>/',
         views.fetch_votes, name='fetch_votes'),
    path('fetch_votes/<int:roulette_id>/success/',
         views.fetch_votes_success, name='fetch_votes_success'),
    path('fetch_votes/<int:roulette_id>/failure/<slug:failure_type>',
         views.fetch_votes_failure, name='fetch_votes_failure'),
]
