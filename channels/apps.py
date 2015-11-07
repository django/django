from django.apps import AppConfig


class ChannelsConfig(AppConfig):

    name = "channels"
    verbose_name = "Channels"

    def ready(self):
        # Do django monkeypatches
        from .hacks import monkeypatch_django
        monkeypatch_django()
