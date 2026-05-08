import contextlib
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


def maybe_aclosing(iterator):
    """
    Wrap an async iterator in contextlib.aclosing() if it has an aclose()
    method, otherwise return it wrapped in contextlib.nullcontext().

    This ensures that async generators are properly closed when iteration
    exits (via break, return, exception, or cancellation), rather than
    deferring cleanup to asyncio's asyncgen finalizer hook.

    See PEP 533 and https://code.djangoproject.com/ticket/35190.
    """
    return (
        contextlib.aclosing(iterator)
        if hasattr(iterator, "aclose")
        else contextlib.nullcontext(iterator)
    )
