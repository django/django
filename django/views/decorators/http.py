"""
Decorators for views based on HTTP headers.
"""

import logging
from calendar import timegm
from functools import wraps

from django.http import HttpResponseNotAllowed
from django.middleware.http import ConditionalGetMiddleware
from django.utils.cache import get_conditional_response
from django.utils.decorators import available_attrs, decorator_from_middleware
from django.utils.http import http_date, quote_etag

conditional_page = decorator_from_middleware(ConditionalGetMiddleware)

logger = logging.getLogger('django.request')


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
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            if request.method not in request_method_list:
                logger.warning(
                    'Method Not Allowed (%s): %s', request.method, request.path,
                    extra={'status_code': 405, 'request': request}
                )
                return HttpResponseNotAllowed(request_method_list)
            return func(request, *args, **kwargs)
        return inner
    return decorator


require_GET = require_http_methods(["GET"])
require_GET.__doc__ = "Decorator to require that a view only accepts the GET method."

require_POST = require_http_methods(["POST"])
require_POST.__doc__ = "Decorator to require that a view only accepts the POST method."

require_safe = require_http_methods(["GET", "HEAD"])
require_safe.__doc__ = "Decorator to require that a view only accepts safe methods: GET and HEAD."


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
    failed), depending upon the request method. In either case, it will add the
    generated ETag and Last-Modified headers to the response if it doesn't
    already have them.
    """
    def decorator(func):
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            # Compute values (if any) for the requested resource.
            def get_last_modified():
                if last_modified_func:
                    dt = last_modified_func(request, *args, **kwargs)
                    if dt:
                        return timegm(dt.utctimetuple())

            # The value from etag_func() could be quoted or unquoted.
            res_etag = etag_func(request, *args, **kwargs) if etag_func else None
            res_etag = quote_etag(res_etag) if res_etag is not None else None
            res_last_modified = get_last_modified()

            response = get_conditional_response(
                request,
                etag=res_etag,
                last_modified=res_last_modified,
            )

            if response is None:
                response = func(request, *args, **kwargs)

            # Set relevant headers on the response if they don't already exist.
            if res_last_modified and not response.has_header('Last-Modified'):
                response['Last-Modified'] = http_date(res_last_modified)
            if res_etag and not response.has_header('ETag'):
                response['ETag'] = res_etag

            return response

        return inner
    return decorator


# Shortcut decorators for common cases based on ETag or Last-Modified only
def etag(etag_func):
    return condition(etag_func=etag_func)


def last_modified(last_modified_func):
    return condition(last_modified_func=last_modified_func)
