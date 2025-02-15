import thibaud
from thibaud.core.handlers.wsgi import WSGIHandler


def get_wsgi_application():
    """
    The public interface to Thibaud's WSGI support. Return a WSGI callable.

    Avoids making thibaud.core.handlers.WSGIHandler a public API, in case the
    internal WSGI implementation changes or moves in the future.
    """
    thibaud.setup(set_prefix=False)
    return WSGIHandler()
