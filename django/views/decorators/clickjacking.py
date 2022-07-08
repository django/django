import asyncio
from functools import wraps

from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def xframe_options_deny(view_func):
    """
    Modify a view function so its response has the X-Frame-Options HTTP
    header set to 'DENY' as long as the response doesn't already have that
    header set. Usage:

    @xframe_options_deny
    def some_view(request):
        ...
    """

    def _process_response(response):
        if response.get("X-Frame-Options") is None:
            response["X-Frame-Options"] = "DENY"

    @wraps(view_func)
    def _wrapper_view_sync(*args, **kwargs):
        response = view_func(*args, **kwargs)
        _process_response(response)
        return response

    @wraps(view_func)
    async def _wrapper_view_async(*args, **kwargs):
        response = await view_func(*args, **kwargs)
        _process_response(response)
        return response

    if asyncio.iscoroutinefunction(view_func):
        return _wrapper_view_async
    return _wrapper_view_sync


@sync_and_async_middleware
def xframe_options_sameorigin(view_func):
    """
    Modify a view function so its response has the X-Frame-Options HTTP
    header set to 'SAMEORIGIN' as long as the response doesn't already have
    that header set. Usage:

    @xframe_options_sameorigin
    def some_view(request):
        ...
    """

    def _process_response(response):
        if response.get("X-Frame-Options") is None:
            response["X-Frame-Options"] = "SAMEORIGIN"

    @wraps(view_func)
    def _wrapper_view_sync(*args, **kwargs):
        response = view_func(*args, **kwargs)
        _process_response(response)
        return response

    @wraps(view_func)
    async def _wrapper_view_async(*args, **kwargs):
        response = await view_func(*args, **kwargs)
        _process_response(response)
        return response

    if asyncio.iscoroutinefunction(view_func):
        return _wrapper_view_async
    return _wrapper_view_sync


def xframe_options_exempt(view_func):
    """
    Modify a view function by setting a response variable that instructs
    XFrameOptionsMiddleware to NOT set the X-Frame-Options HTTP header. Usage:

    @xframe_options_exempt
    def some_view(request):
        ...
    """

    @wraps(view_func)
    def wrapper_view(*args, **kwargs):
        resp = view_func(*args, **kwargs)
        resp.xframe_options_exempt = True
        return resp

    return wrapper_view
