from __future__ import unicode_literals

import logging
import sys

from django.conf import settings
from django.core import signals
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.http.multipartparser import MultiPartParserError
from django.urls import get_resolver, get_urlconf
from django.utils.encoding import force_text
from django.views import debug

logger = logging.getLogger('django.request')


class ExceptionMiddleware(object):
    """
    Convert selected exceptions to HTTP responses.

    For example, convert Http404 to a 404 response either through handler404
    or through the debug view if settings.DEBUG=True. To ensure that
    exceptions raised by other middleware are converted to the appropriate
    response, this middleware is always automatically applied as the outermost
    middleware.
    """
    def __init__(self, get_response, handler=None):
        from django.core.handlers.base import BaseHandler
        self.get_response = get_response
        self.handler = handler or BaseHandler()

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Http404 as exc:
            if settings.DEBUG:
                response = debug.technical_404_response(request, exc)
            else:
                response = self.handler.get_exception_response(request, get_resolver(get_urlconf()), 404, exc)

        except PermissionDenied as exc:
            logger.warning(
                'Forbidden (Permission denied): %s', request.path,
                extra={'status_code': 403, 'request': request},
            )
            response = self.handler.get_exception_response(request, get_resolver(get_urlconf()), 403, exc)

        except MultiPartParserError as exc:
            logger.warning(
                'Bad request (Unable to parse request body): %s', request.path,
                extra={'status_code': 400, 'request': request},
            )
            response = self.handler.get_exception_response(request, get_resolver(get_urlconf()), 400, exc)

        except SuspiciousOperation as exc:
            # The request logger receives events for any problematic request
            # The security logger receives events for all SuspiciousOperations
            security_logger = logging.getLogger('django.security.%s' % exc.__class__.__name__)
            security_logger.error(
                force_text(exc),
                extra={'status_code': 400, 'request': request},
            )
            if settings.DEBUG:
                return debug.technical_500_response(request, *sys.exc_info(), status_code=400)

            response = self.handler.get_exception_response(request, get_resolver(get_urlconf()), 400, exc)

        except SystemExit:
            # Allow sys.exit() to actually exit. See tickets #1023 and #4701
            raise

        except Exception:  # Handle everything else.
            # Get the exception info now, in case another exception is thrown later.
            signals.got_request_exception.send(sender=self.handler.__class__, request=request)
            response = self.handler.handle_uncaught_exception(request, get_resolver(get_urlconf()), sys.exc_info())

        return response
