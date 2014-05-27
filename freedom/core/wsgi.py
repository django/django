import freedom
from freedom.core.handlers.wsgi import WSGIHandler


def get_wsgi_application():
    """
    The public interface to Freedom's WSGI support. Should return a WSGI
    callable.

    Allows us to avoid making freedom.core.handlers.WSGIHandler public API, in
    case the internal WSGI implementation changes or moves in the future.

    """
    freedom.setup()
    return WSGIHandler()
