import os
from asyncio import get_running_loop
from functools import wraps

from django.core.exceptions import SynchronousOnlyOperation


def async_unsafe(message):
    """
    Decorator to mark functions as async-unsafe. Someone trying to access
    the function while in an async context will get an error message.
    """

    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            # Detect a running event loop in this thread.
            try:
                get_running_loop()
            except RuntimeError:
                pass
            else:
                if not os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE"):
                    raise SynchronousOnlyOperation(message)
            # Pass onward.
            return func(*args, **kwargs)

        return inner

    # If the message is actually a function, then be a no-arguments decorator.
    if callable(message):
        func = message
        message = (
            "You cannot call this from an async context - use a thread or "
            "sync_to_async."
        )
        return decorator(func)
    else:
        return decorator


try:
    from contextlib import aclosing
except ImportError:
    # TODO: Remove when dropping support for PY39.
    from contextlib import AbstractAsyncContextManager

    # Backport of contextlib.aclosing() from Python 3.10. Copyright (C) Python
    # Software Foundation (see LICENSE.python).
    class aclosing(AbstractAsyncContextManager):
        """
        Async context manager for safely finalizing an asynchronously
        cleaned-up resource such as an async generator, calling its
        ``aclose()`` method.
        """

        def __init__(self, thing):
            self.thing = thing

        async def __aenter__(self):
            return self.thing

        async def __aexit__(self, *exc_info):
            await self.thing.aclose()
