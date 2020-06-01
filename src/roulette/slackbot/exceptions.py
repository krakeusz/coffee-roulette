

class SlackbotError(Exception):
    """ Base class for exceptions defined in this module. """
    pass


class NoWorkspaceError(SlackbotError):
    def __init__(self):
        super().__init__("The Slack workspace hasn't been connected to this app.")
