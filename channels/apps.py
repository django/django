from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class ChannelsConfig(AppConfig):

    name = "channels"
    verbose_name = "Channels"

    def ready(self):
        # Check you're not running 1.10 or above
        try:
            from django import channels  # NOQA isort:skip
        except ImportError:
            pass
        else:
            raise ImproperlyConfigured("You have Django 1.10 or above; use the builtin django.channels!")
        # Do django monkeypatches
        from .hacks import monkeypatch_django
        monkeypatch_django()
