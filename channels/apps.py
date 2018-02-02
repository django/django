from django.apps import AppConfig

# We import this here to ensure the reactor is installed very early on
# in case other packages accidentally import twisted.internet.reactor
# (e.g. raven does this).
import daphne.server  # noqa


class ChannelsConfig(AppConfig):

    name = "channels"
    verbose_name = "Channels"

    def ready(self):
        # Do django monkeypatches
        from .hacks import monkeypatch_django
        monkeypatch_django()
