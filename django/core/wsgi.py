from django.apps import apps
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler


def get_wsgi_application():
    """
    The public interface to Django's WSGI support. Should return a WSGI
    callable.

    Allows us to avoid making django.core.handlers.WSGIHandler public API, in
    case the internal WSGI implementation changes or moves in the future.

    """
    # Configure the settings (this happens automatically on the first access).
    # Populate the app registry.
    apps.populate_apps(settings.INSTALLED_APPS)
    apps.populate_models()

    return WSGIHandler()
