"""
Decorators for views based on HTTP headers.
"""
import asyncio
import datetime
from functools import wraps

from django.http import HttpResponseNotAllowed
from django.middleware.http import ConditionalGetMiddleware
from django.utils import timezone
from django.utils.cache import get_conditional_response
from django.utils.decorators import decorator_from_middleware, sync_and_async_middleware
from django.utils.http import http_date, quote_etag
from django.utils.log import log_response

conditional_page = decorator_from_middleware(ConditionalGetMiddleware)
conditional_page = sync_and_async_middleware(conditional_page)


@sync_and_async_middleware
def require_http_methods(request_method_list):
    """
    Decorator to make a view only accept particular request methods.  Usage::

        @require_http_methods(["GET", "POST"])
        def my_view(request):
            # I can assume now that only GET or POST requests make it this far
            # ...

    Note that request methods should be in uppercase.
    """

    def decorator(func):
        def _process_request(request):
            if request.method not in request_method_list:
                response = HttpResponseNotAllowed(request_method_list)
                log_response(
                    "Method Not Allowed (%s): %s",
                    request.method,
                    request.path,
                    response=response,
                    request=request,
                )
                return response

        @wraps(func)
        def _wrapper_view_sync(request, *args, **kwargs):
            response = _process_request(request)
            if response is not None:
                return response

            return func(request)

        @wraps(func)
        async def _wrapper_view_async(request, *args, **kwargs):
            response = _process_request(request)
            if response is not None:
                return response

            return await func(request)

        if asyncio.iscoroutinefunction(func):
            return _wrapper_view_async
        return _wrapper_view_sync

    return decorator


require_GET = require_http_methods(["GET"])
require_GET.__doc__ = "Decorator to require that a view only accepts the GET method."
require_GET = sync_and_async_middleware(require_GET)

require_POST = require_http_methods(["POST"])
require_POST.__doc__ = "Decorator to require that a view only accepts the POST method."
require_POST = sync_and_async_middleware(require_POST)

require_safe = require_http_methods(["GET", "HEAD"])
require_safe.__doc__ = (
    "Decorator to require that a view only accepts safe methods: GET and HEAD."
)
require_safe = sync_and_async_middleware(require_safe)


@sync_and_async_middleware
def condition(etag_func=None, last_modified_func=None):
    """
    Decorator to support conditional retrieval (or change) for a view
    function.

    The parameters are callables to compute the ETag and last modified time for
    the requested resource, respectively. The callables are passed the same
    parameters as the view itself. The ETag function should return a string (or
    None if the resource doesn't exist), while the last_modified function
    should return a datetime object (or None if the resource doesn't exist).

    The ETag function should return a complete ETag, including quotes (e.g.
    '"etag"'), since that's the only way to distinguish between weak and strong
    ETags. If an unquoted ETag is returned (e.g. 'etag'), it will be converted
    to a strong ETag by adding quotes.

    This decorator will either pass control to the wrapped view function or
    return an HTTP 304 response (unmodified) or 412 response (precondition
    failed), depending upon the request method. In either case, the decorator
    will add the generated ETag and Last-Modified headers to the response if
    the headers aren't already set and if the request's method is safe.
    """

    def decorator(func):
        def _get_res_etag(request, *args, **kwargs):
            # The value from etag_func() could be quoted or unquoted.
            res_etag = etag_func(request, *args, **kwargs) if etag_func else None
            res_etag = quote_etag(res_etag) if res_etag is not None else None
            return res_etag

        def _get_last_modified(request, *args, **kwargs):
            # Compute values (if any) for the requested resource.
            if last_modified_func:
                dt = last_modified_func(request, *args, **kwargs)
                if dt:
                    if not timezone.is_aware(dt):
                        dt = timezone.make_aware(dt, datetime.timezone.utc)
                    return int(dt.timestamp())

        def _process_response(request, response, res_etag, res_last_modified):
            # Set relevant headers on the response if they don't already exist
            # and if the request method is safe.
            if request.method in ("GET", "HEAD"):
                if res_last_modified and not response.has_header("Last-Modified"):
                    response.headers["Last-Modified"] = http_date(res_last_modified)
                if res_etag:
                    response.headers.setdefault("ETag", res_etag)

        @wraps(func)
        def _wrapper_view_sync(request, *args, **kwargs):
            res_etag = _get_res_etag(request, *args, **kwargs)
            res_last_modified = _get_last_modified(request, *args, **kwargs)

            response = get_conditional_response(
                request,
                etag=res_etag,
                last_modified=res_last_modified,
            )

            if response is None:
                response = func(request, *args, **kwargs)

            _process_response(request, response, res_etag, res_last_modified)

            return response

        @wraps(func)
        async def _wrapper_view_async(request, *args, **kwargs):
            res_etag = _get_res_etag(request, *args, **kwargs)
            res_last_modified = _get_last_modified(request, *args, **kwargs)

            response = get_conditional_response(
                request,
                etag=res_etag,
                last_modified=res_last_modified,
            )

            if response is None:
                response = await func(request, *args, **kwargs)

            _process_response(request, response, res_etag, res_last_modified)

            return response

        if asyncio.iscoroutinefunction(func):
            return _wrapper_view_async
        return _wrapper_view_sync

    return decorator


# Shortcut decorators for common cases based on ETag or Last-Modified only
@sync_and_async_middleware
def etag(etag_func):
    return condition(etag_func=etag_func)


@sync_and_async_middleware
def last_modified(last_modified_func):
    return condition(last_modified_func=last_modified_func)
