from django.apps import AppConfig


class SlackbotConfig(AppConfig):
    name = 'slackbot'

    def ready(self):
        from .signals import broadcast_new_roulette, broadcast_matching_results
