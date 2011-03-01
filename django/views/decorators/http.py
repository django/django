"""
Decorators for views based on HTTP headers.
"""

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

from calendar import timegm
from datetime import timedelta

from django.utils.decorators import decorator_from_middleware, available_attrs
from django.utils.http import http_date, parse_http_date_safe, parse_etags, quote_etag
from django.middleware.http import ConditionalGetMiddleware
from django.http import HttpResponseNotAllowed, HttpResponseNotModified, HttpResponse


conditional_page = decorator_from_middleware(ConditionalGetMiddleware)

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
        def inner(request, *args, **kwargs):
            if request.method not in request_method_list:
                return HttpResponseNotAllowed(request_method_list)
            return func(request, *args, **kwargs)
        return wraps(func, assigned=available_attrs(func))(inner)
    return decorator

require_GET = require_http_methods(["GET"])
require_GET.__doc__ = "Decorator to require that a view only accept the GET method."

require_POST = require_http_methods(["POST"])
require_POST.__doc__ = "Decorator to require that a view only accept the POST method."

def condition(etag_func=None, last_modified_func=None):
    """
    Decorator to support conditional retrieval (or change) for a view
    function.

    The parameters are callables to compute the ETag and last modified time for
    the requested resource, respectively. The callables are passed the same
    parameters as the view itself. The Etag function should return a string (or
    None if the resource doesn't exist), whilst the last_modified function
    should return a datetime object (or None if the resource doesn't exist).

    If both parameters are provided, all the preconditions must be met before
    the view is processed.

    This decorator will either pass control to the wrapped view function or
    return an HTTP 304 response (unmodified) or 412 response (preconditions
    failed), depending upon the request method.

    Any behavior marked as "undefined" in the HTTP spec (e.g. If-none-match
    plus If-modified-since headers) will result in the view function being
    called.
    """
    def decorator(func):
        def inner(request, *args, **kwargs):
            # Get HTTP request headers
            if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE")
            if if_modified_since:
                if_modified_since = parse_http_date_safe(if_modified_since)
            if_none_match = request.META.get("HTTP_IF_NONE_MATCH")
            if_match = request.META.get("HTTP_IF_MATCH")
            if if_none_match or if_match:
                # There can be more than one ETag in the request, so we
                # consider the list of values.
                try:
                    etags = parse_etags(if_none_match or if_match)
                except ValueError:
                    # In case of invalid etag ignore all ETag headers.
                    # Apparently Opera sends invalidly quoted headers at times
                    # (we should be returning a 400 response, but that's a
                    # little extreme) -- this is Django bug #10681.
                    if_none_match = None
                    if_match = None

            # Compute values (if any) for the requested resource.
            if etag_func:
                res_etag = etag_func(request, *args, **kwargs)
            else:
                res_etag = None
            if last_modified_func:
                dt = last_modified_func(request, *args, **kwargs)
                if dt:
                    res_last_modified = timegm(dt.utctimetuple())
                else:
                    res_last_modified = None
            else:
                res_last_modified = None

            response = None
            if not ((if_match and (if_modified_since or if_none_match)) or
                    (if_match and if_none_match)):
                # We only get here if no undefined combinations of headers are
                # specified.
                if ((if_none_match and (res_etag in etags or
                        "*" in etags and res_etag)) and
                        (not if_modified_since or
                            (res_last_modified and if_modified_since and
                            res_last_modified <= if_modified_since))):
                    if request.method in ("GET", "HEAD"):
                        response = HttpResponseNotModified()
                    else:
                        response = HttpResponse(status=412)
                elif if_match and ((not res_etag and "*" in etags) or
                        (res_etag and res_etag not in etags)):
                    response = HttpResponse(status=412)
                elif (not if_none_match and request.method == "GET" and
                        res_last_modified and if_modified_since and
                        res_last_modified <= if_modified_since):
                    response = HttpResponseNotModified()

            if response is None:
                response = func(request, *args, **kwargs)

            # Set relevant headers on the response if they don't already exist.
            if res_last_modified and not response.has_header('Last-Modified'):
                response['Last-Modified'] = http_date(res_last_modified)
            if res_etag and not response.has_header('ETag'):
                response['ETag'] = quote_etag(res_etag)

            return response

        return inner
    return decorator

# Shortcut decorators for common cases based on ETag or Last-Modified only
def etag(etag_func):
    return condition(etag_func=etag_func)

def last_modified(last_modified_func):
    return condition(last_modified_func=last_modified_func)

