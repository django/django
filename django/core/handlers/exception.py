from __future__ import unicode_literals

import logging
import sys
import warnings
from functools import wraps

from django.conf import settings
from django.core import signals
from django.core.exceptions import (
    PermissionDenied, RequestDataTooBig, SuspiciousOperation,
    TooManyFieldsSent,
)
from django.http import Http404
from django.http.multipartparser import MultiPartParserError
from django.urls import get_resolver, get_urlconf
from django.utils import six
from django.utils.decorators import available_attrs
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text
from django.views import debug

logger = logging.getLogger('django.request')


def convert_exception_to_response(get_response):
    """
    Wrap the given get_response callable in exception-to-response conversion.

    All exceptions will be converted. All known 4xx exceptions (Http404,
    PermissionDenied, MultiPartParserError, SuspiciousOperation) will be
    converted to the appropriate response, and all other exceptions will be
    converted to 500 responses.

    This decorator is automatically applied to all middleware to ensure that
    no middleware leaks an exception and that the next middleware in the stack
    can rely on getting a response instead of an exception.
    """
    @wraps(get_response, assigned=available_attrs(get_response))
    def inner(request):
        try:
            response = get_response(request)
        except Exception as exc:
            response = response_for_exception(request, exc)
        return response
    return inner


def response_for_exception(request, exc):
    if isinstance(exc, Http404):
        if settings.DEBUG:
            response = debug.technical_404_response(request, exc)
        else:
            response = get_exception_response(request, get_resolver(get_urlconf()), 404, exc)

    elif isinstance(exc, PermissionDenied):
        logger.warning(
            'Forbidden (Permission denied): %s', request.path,
            extra={'status_code': 403, 'request': request},
        )
        response = get_exception_response(request, get_resolver(get_urlconf()), 403, exc)

    elif isinstance(exc, MultiPartParserError):
        logger.warning(
            'Bad request (Unable to parse request body): %s', request.path,
            extra={'status_code': 400, 'request': request},
        )
        response = get_exception_response(request, get_resolver(get_urlconf()), 400, exc)

    elif isinstance(exc, SuspiciousOperation):
        if isinstance(exc, (RequestDataTooBig, TooManyFieldsSent)):
            # POST data can't be accessed again, otherwise the original
            # exception would be raised.
            request._mark_post_parse_error()

        # The request logger receives events for any problematic request
        # The security logger receives events for all SuspiciousOperations
        security_logger = logging.getLogger('django.security.%s' % exc.__class__.__name__)
        security_logger.error(
            force_text(exc),
            extra={'status_code': 400, 'request': request},
        )
        if settings.DEBUG:
            response = debug.technical_500_response(request, *sys.exc_info(), status_code=400)
        else:
            response = get_exception_response(request, get_resolver(get_urlconf()), 400, exc)

    elif isinstance(exc, SystemExit):
        # Allow sys.exit() to actually exit. See tickets #1023 and #4701
        raise

    else:
        signals.got_request_exception.send(sender=None, request=request)
        response = handle_uncaught_exception(request, get_resolver(get_urlconf()), sys.exc_info())

    return response


def get_exception_response(request, resolver, status_code, exception, sender=None):
    try:
        callback, param_dict = resolver.resolve_error_handler(status_code)
        # Unfortunately, inspect.getargspec result is not trustable enough
        # depending on the callback wrapping in decorators (frequent for handlers).
        # Falling back on try/except:
        try:
            response = callback(request, **dict(param_dict, exception=exception))
        except TypeError:
            warnings.warn(
                "Error handlers should accept an exception parameter. Update "
                "your code as this parameter will be required in Django 2.0",
                RemovedInDjango20Warning, stacklevel=2
            )
            response = callback(request, **param_dict)
    except Exception:
        signals.got_request_exception.send(sender=sender, request=request)
        response = handle_uncaught_exception(request, resolver, sys.exc_info())

    return response


def handle_uncaught_exception(request, resolver, exc_info):
    """
    Processing for any otherwise uncaught exceptions (those that will
    generate HTTP 500 responses).
    """
    if settings.DEBUG_PROPAGATE_EXCEPTIONS:
        raise

    logger.error(
        'Internal Server Error: %s', request.path,
        exc_info=exc_info,
        extra={'status_code': 500, 'request': request},
    )

    if settings.DEBUG:
        return debug.technical_500_response(request, *exc_info)

    # If Http500 handler is not installed, reraise the last exception.
    if resolver.urlconf_module is None:
        six.reraise(*exc_info)
    # Return an HttpResponse that displays a friendly error message.
    callback, param_dict = resolver.resolve_error_handler(500)
    return callback(request, **param_dict)
