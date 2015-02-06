import django
from django.core.handlers.wsgi import WSGIHandler

try:
    import gunicorn
except ImportError:
    gunicorn = None


def get_wsgi_application():
    """
    The public interface to Django's WSGI support. Should return a WSGI
    callable.

    Allows us to avoid making django.core.handlers.WSGIHandler public API, in
    case the internal WSGI implementation changes or moves in the future.

    """
    django.setup()
    from django.conf import settings
    # activate static files support for gunicorn if DEBUG is set to True
    if settings.DEBUG and gunicorn is not None:
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        return StaticFilesHandler(WSGIHandler())
    return WSGIHandler()
