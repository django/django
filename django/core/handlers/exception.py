import asyncio
import logging
import sys
from functools import wraps

from asgiref.sync import sync_to_async

from django.conf import settings
from django.core import signals
from django.core.exceptions import (
    BadRequest, PermissionDenied, RequestDataTooBig, SuspiciousOperation,
    TooManyFieldsSent, TooManyFilesSent,
)
from django.http import Http404
from django.http.multipartparser import MultiPartParserError
from django.urls import get_resolver, get_urlconf
from django.utils.log import log_response
from django.views import debug


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
    if asyncio.iscoroutinefunction(get_response):
        @wraps(get_response)
        async def inner(request):
            try:
                response = await get_response(request)
            except Exception as exc:
                response = await sync_to_async(response_for_exception, thread_sensitive=False)(request, exc)
            return response
        return inner
    else:
        @wraps(get_response)
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
        response = get_exception_response(request, get_resolver(get_urlconf()), 403, exc)
        log_response(
            'Forbidden (Permission denied): %s', request.path,
            response=response,
            request=request,
            exc_info=sys.exc_info(),
        )

    elif isinstance(exc, MultiPartParserError):
        response = get_exception_response(request, get_resolver(get_urlconf()), 400, exc)
        log_response(
            'Bad request (Unable to parse request body): %s', request.path,
            response=response,
            request=request,
            exc_info=sys.exc_info(),
        )

    elif isinstance(exc, BadRequest):
        if settings.DEBUG:
            response = debug.technical_500_response(request, *sys.exc_info(), status_code=400)
        else:
            response = get_exception_response(request, get_resolver(get_urlconf()), 400, exc)
        log_response(
            '%s: %s', str(exc), request.path,
            response=response,
            request=request,
            exc_info=sys.exc_info(),
        )
    elif isinstance(exc, SuspiciousOperation):
        if isinstance(exc, (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent)):
            # POST data can't be accessed again, otherwise the original
            # exception would be raised.
            request._mark_post_parse_error()

        # The request logger receives events for any problematic request
        # The security logger receives events for all SuspiciousOperations
        security_logger = logging.getLogger('django.security.%s' % exc.__class__.__name__)
        security_logger.error(
            str(exc),
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
        log_response(
            '%s: %s', response.reason_phrase, request.path,
            response=response,
            request=request,
            exc_info=sys.exc_info(),
        )

    # Force a TemplateResponse to be rendered.
    if not getattr(response, 'is_rendered', True) and callable(getattr(response, 'render', None)):
        response = response.render()

    return response


def get_exception_response(request, resolver, status_code, exception):
    try:
        callback = resolver.resolve_error_handler(status_code)
        response = callback(request, exception=exception)
    except Exception:
        signals.got_request_exception.send(sender=None, request=request)
        response = handle_uncaught_exception(request, resolver, sys.exc_info())

    return response


def handle_uncaught_exception(request, resolver, exc_info):
    """
    Processing for any otherwise uncaught exceptions (those that will
    generate HTTP 500 responses).
    """
    if settings.DEBUG_PROPAGATE_EXCEPTIONS:
        raise

    if settings.DEBUG:
        return debug.technical_500_response(request, *exc_info)

    # Return an HttpResponse that displays a friendly error message.
    callback = resolver.resolve_error_handler(500)
    return callback(request)
