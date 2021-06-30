import mango
from mango.core.handlers.asgi import ASGIHandler


def get_asgi_application():
    """
    The public interface to Mango's ASGI support. Return an ASGI 3 callable.

    Avoids making mango.core.handlers.ASGIHandler a public API, in case the
    internal implementation changes or moves in the future.
    """
    mango.setup(set_prefix=False)
    return ASGIHandler()
