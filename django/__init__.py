VERSION = (1, 7, 0, 'alpha', 0)


def get_version(*args, **kwargs):
    # Don't litter django/__init__.py with all the get_version stuff.
    # Only import if it's actually called.
    from django.utils.version import get_version
    return get_version(*args, **kwargs)


def setup():
    # Configure the settings (this happens as a side effect of accessing
    # INSTALLED_APPS or any other setting) and populate the app registry.
    from django.apps import apps
    from django.conf import settings
    apps.populate_apps(settings.INSTALLED_APPS)
    apps.populate_models()
