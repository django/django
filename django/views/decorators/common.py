import asyncio
from functools import wraps

from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def no_append_slash(view_func):
    """
    Mark a view function as excluded from CommonMiddleware's APPEND_SLASH
    redirection.
    """
    # view_func.should_append_slash = False would also work, but decorators are
    # nicer if they don't have side effects, so return a new function.
    @wraps(view_func)
    def _wrapper_view_sync(*args, **kwargs):
        return view_func(*args, **kwargs)

    @wraps(view_func)
    async def _wrapper_view_async(*args, **kwargs):
        return await view_func(*args, **kwargs)

    if asyncio.iscoroutinefunction(view_func):
        wrapper_view = _wrapper_view_async
    else:
        wrapper_view = _wrapper_view_sync

    wrapper_view.should_append_slash = False
    return wrapper_view
