from django.apps import AppConfig


class MatcherConfig(AppConfig):
    name = 'matcher'

    def ready(self):
        from .signals import add_default_votes, add_user_to_active_roulettes
