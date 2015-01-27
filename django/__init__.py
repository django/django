VERSION = (1, 7, 4, 'final', 0)


def get_version(*args, **kwargs):
    # Don't litter django/__init__.py with all the get_version stuff.
    # Only import if it's actually called.
    from django.utils.version import get_version
    return get_version(*args, **kwargs)


def setup():
    """
    Configure the settings (this happens as a side effect of accessing the
    first setting), configure logging and populate the app registry.
    """
    from django.apps import apps
    from django.conf import settings
    from django.utils.log import configure_logging

    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
    apps.populate(settings.INSTALLED_APPS)
