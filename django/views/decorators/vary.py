import asyncio
from functools import wraps

from django.utils.cache import patch_vary_headers
from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def vary_on_headers(*headers):
    """
    A view decorator that adds the specified headers to the Vary header of the
    response. Usage:

       @vary_on_headers('Cookie', 'Accept-language')
       def index(request):
           ...

    Note that the header names are not case-sensitive.
    """

    def decorator(func):
        def _process_response(response):
            patch_vary_headers(response, headers)

        @wraps(func)
        def _wrapper_view_sync(*args, **kwargs):
            response = func(*args, **kwargs)
            _process_response(response)
            return response

        @wraps(func)
        async def _wrapper_view_async(*args, **kwargs):
            response = await func(*args, **kwargs)
            _process_response(response)
            return response

        if asyncio.iscoroutinefunction(func):
            return _wrapper_view_async
        return _wrapper_view_sync

    return decorator


@sync_and_async_middleware
def vary_on_cookie(func):
    """
    A view decorator that adds "Cookie" to the Vary header of a response. This
    indicates that a page's contents depends on cookies. Usage:

        @vary_on_cookie
        def index(request):
            ...
    """

    def _process_response(response):
        patch_vary_headers(response, ("Cookie",))

    @wraps(func)
    def _wrapper_view_sync(*args, **kwargs):
        response = func(*args, **kwargs)
        _process_response(response)
        return response

    @wraps(func)
    async def _wrapper_view_async(*args, **kwargs):
        response = await func(*args, **kwargs)
        _process_response(response)
        return response

    if asyncio.iscoroutinefunction(func):
        return _wrapper_view_async
    return _wrapper_view_sync
