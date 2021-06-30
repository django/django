import mango
from mango.core.handlers.wsgi import WSGIHandler


def get_wsgi_application():
    """
    The public interface to Mango's WSGI support. Return a WSGI callable.

    Avoids making mango.core.handlers.WSGIHandler a public API, in case the
    internal WSGI implementation changes or moves in the future.
    """
    mango.setup(set_prefix=False)
    return WSGIHandler()
