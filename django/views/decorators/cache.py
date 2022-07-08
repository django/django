import asyncio
from functools import wraps

from django.middleware.cache import CacheMiddleware
from django.utils.cache import add_never_cache_headers, patch_cache_control
from django.utils.decorators import (
    decorator_from_middleware_with_args,
    sync_and_async_middleware,
)


def cache_page(timeout, *, cache=None, key_prefix=None):
    """
    Decorator for views that tries getting the page from the cache and
    populates the cache if the page isn't in the cache yet.

    The cache is keyed by the URL and some data from the headers.
    Additionally there is the key prefix that is used to distinguish different
    cache areas in a multi-site setup. You could use the
    get_current_site().domain, for example, as that is unique across a Django
    project.

    Additionally, all headers from the response's Vary header will be taken
    into account on caching -- just like the middleware does.
    """
    return decorator_from_middleware_with_args(CacheMiddleware)(
        page_timeout=timeout,
        cache_alias=cache,
        key_prefix=key_prefix,
    )


@sync_and_async_middleware
def cache_control(**kwargs):
    def _cache_controller(viewfunc):
        def _process_request(request):
            # Ensure argument looks like a request.
            if not hasattr(request, "META"):
                raise TypeError(
                    "cache_control didn't receive an HttpRequest. If you are "
                    "decorating a classmethod, be sure to use "
                    "@method_decorator."
                )

        def _process_response(response, **kwargs):
            patch_cache_control(response, **kwargs)

        @wraps(viewfunc)
        def _wrapper_view_sync(request, *args, **kw):
            _process_request(request)
            response = viewfunc(request, *args, **kw)
            _process_response(response, **kwargs)
            return response

        @wraps(viewfunc)
        async def _wrapper_view_async(request, *args, **kw):
            _process_request(request)
            response = await viewfunc(request, *args, **kw)
            _process_response(response, **kwargs)
            return response

        if asyncio.iscoroutinefunction(viewfunc):
            return _wrapper_view_async
        return _wrapper_view_sync

    return _cache_controller


def never_cache(view_func):
    """
    Decorator that adds headers to a response so that it will never be cached.
    """

    @wraps(view_func)
    def _wrapper_view_func(request, *args, **kwargs):
        # Ensure argument looks like a request.
        if not hasattr(request, "META"):
            raise TypeError(
                "never_cache didn't receive an HttpRequest. If you are "
                "decorating a classmethod, be sure to use @method_decorator."
            )
        response = view_func(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response

    return _wrapper_view_func
