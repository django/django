import asyncio
import functools
import os

from django.core.exceptions import SynchronousOnlyOperation
from django.utils.version import PY37


if PY37:
    get_running_loop = asyncio.get_running_loop
else:
    get_running_loop = asyncio.get_event_loop


def async_unsafe(message):
    """
    Decorator to mark functions as async-unsafe. Someone trying to access
    the function while in an async context will get an error message.
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if not os.environ.get('DJANGO_ALLOW_ASYNC_UNSAFE'):
                # Detect a running event loop in this thread.
                try:
                    event_loop = get_running_loop()
                except RuntimeError:
                    pass
                else:
                    if PY37 or event_loop.is_running():
                        raise SynchronousOnlyOperation(message)
            # Pass onwards.
            return func(*args, **kwargs)
        return inner
    # If the message is actually a function, then be a no-arguments decorator.
    if callable(message):
        func = message
        message = 'You cannot call this from an async context - use a thread or sync_to_async.'
        return decorator(func)
    else:
        return decorator
