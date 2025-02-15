import thibaud
from thibaud.core.handlers.asgi import ASGIHandler


def get_asgi_application():
    """
    The public interface to Thibaud's ASGI support. Return an ASGI 3 callable.

    Avoids making thibaud.core.handlers.ASGIHandler a public API, in case the
    internal implementation changes or moves in the future.
    """
    thibaud.setup(set_prefix=False)
    return ASGIHandler()
