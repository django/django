from __future__ import unicode_literals

import logging
import sys
import types

from django import http
from django.conf import settings
from django.core import urlresolvers
from django.core import signals
from django.core.exceptions import MiddlewareNotUsed, PermissionDenied, SuspiciousOperation
from django.db import connections, transaction
from django.utils.encoding import force_text
from django.utils.module_loading import import_string
from django.utils import six
from django.views import debug

logger = logging.getLogger('django.request')


class BaseHandler(object):
    # Changes that are always applied to a response (in this order).
    response_fixes = [
        http.fix_location_header,
        http.conditional_content_removal,
    ]

    def __init__(self):
        self._request_middleware = self._view_middleware = self._template_response_middleware = self._response_middleware = self._exception_middleware = None

    def load_middleware(self):
        """
        Populate middleware lists from settings.MIDDLEWARE_CLASSES.

        Must be called after the environment is fixed (see __call__ in subclasses).
        """
        self._view_middleware = []
        self._template_response_middleware = []
        self._response_middleware = []
        self._exception_middleware = []

        request_middleware = []
        for middleware_path in settings.MIDDLEWARE_CLASSES:
            mw_class = import_string(middleware_path)
            try:
                mw_instance = mw_class()
            except MiddlewareNotUsed:
                continue

            if hasattr(mw_instance, 'process_request'):
                request_middleware.append(mw_instance.process_request)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.append(mw_instance.process_view)
            if hasattr(mw_instance, 'process_template_response'):
                self._template_response_middleware.insert(0, mw_instance.process_template_response)
            if hasattr(mw_instance, 'process_response'):
                self._response_middleware.insert(0, mw_instance.process_response)
            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.insert(0, mw_instance.process_exception)

        # We only assign to this when initialization is complete as it is used
        # as a flag for initialization being complete.
        self._request_middleware = request_middleware

    def make_view_atomic(self, view):
        non_atomic_requests = getattr(view, '_non_atomic_requests', set())
        for db in connections.all():
            if (db.settings_dict['ATOMIC_REQUESTS']
                    and db.alias not in non_atomic_requests):
                view = transaction.atomic(using=db.alias)(view)
        return view

    def get_response(self, request):
        "Returns an HttpResponse object for the given HttpRequest"

        # Setup default url resolver for this thread, this code is outside
        # the try/except so we don't get a spurious "unbound local
        # variable" exception in the event an exception is raised before
        # resolver is set
        urlconf = settings.ROOT_URLCONF
        urlresolvers.set_urlconf(urlconf)
        resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
        try:
            response = None
            # Apply request middleware
            for middleware_method in self._request_middleware:
                response = middleware_method(request)
                if response:
                    break

            if response is None:
                if hasattr(request, 'urlconf'):
                    # Reset url resolver with a custom urlconf.
                    urlconf = request.urlconf
                    urlresolvers.set_urlconf(urlconf)
                    resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)

                resolver_match = resolver.resolve(request.path_info)
                callback, callback_args, callback_kwargs = resolver_match
                request.resolver_match = resolver_match

                # Apply view middleware
                for middleware_method in self._view_middleware:
                    response = middleware_method(request, callback, callback_args, callback_kwargs)
                    if response:
                        break

            if response is None:
                wrapped_callback = self.make_view_atomic(callback)
                try:
                    response = wrapped_callback(request, *callback_args, **callback_kwargs)
                except Exception as e:
                    # If the view raised an exception, run it through exception
                    # middleware, and if the exception middleware returns a
                    # response, use that. Otherwise, reraise the exception.
                    for middleware_method in self._exception_middleware:
                        response = middleware_method(request, e)
                        if response:
                            break
                    if response is None:
                        raise

            # Complain if the view returned None (a common error).
            if response is None:
                if isinstance(callback, types.FunctionType):    # FBV
                    view_name = callback.__name__
                else:                                           # CBV
                    view_name = callback.__class__.__name__ + '.__call__'
                raise ValueError("The view %s.%s didn't return an HttpResponse object. It returned None instead."
                                 % (callback.__module__, view_name))

            # If the response supports deferred rendering, apply template
            # response middleware and then render the response
            if hasattr(response, 'render') and callable(response.render):
                for middleware_method in self._template_response_middleware:
                    response = middleware_method(request, response)
                response = response.render()

        except http.Http404 as e:
            logger.warning('Not Found: %s', request.path,
                        extra={
                            'status_code': 404,
                            'request': request
                        })
            if settings.DEBUG:
                response = debug.technical_404_response(request, e)
            else:
                try:
                    callback, param_dict = resolver.resolve404()
                    response = callback(request, **param_dict)
                except:
                    signals.got_request_exception.send(sender=self.__class__, request=request)
                    response = self.handle_uncaught_exception(request, resolver, sys.exc_info())

        except PermissionDenied:
            logger.warning(
                'Forbidden (Permission denied): %s', request.path,
                extra={
                    'status_code': 403,
                    'request': request
                })
            try:
                callback, param_dict = resolver.resolve403()
                response = callback(request, **param_dict)
            except:
                signals.got_request_exception.send(
                    sender=self.__class__, request=request)
                response = self.handle_uncaught_exception(request,
                    resolver, sys.exc_info())

        except SuspiciousOperation as e:
            # The request logger receives events for any problematic request
            # The security logger receives events for all SuspiciousOperations
            security_logger = logging.getLogger('django.security.%s' %
                            e.__class__.__name__)
            security_logger.error(
                force_text(e),
                extra={
                    'status_code': 400,
                    'request': request
                })

            try:
                callback, param_dict = resolver.resolve400()
                response = callback(request, **param_dict)
            except:
                signals.got_request_exception.send(
                    sender=self.__class__, request=request)
                response = self.handle_uncaught_exception(request,
                    resolver, sys.exc_info())

        except SystemExit:
            # Allow sys.exit() to actually exit. See tickets #1023 and #4701
            raise

        except:  # Handle everything else.
            # Get the exception info now, in case another exception is thrown later.
            signals.got_request_exception.send(sender=self.__class__, request=request)
            response = self.handle_uncaught_exception(request, resolver, sys.exc_info())

        try:
            # Apply response middleware, regardless of the response
            for middleware_method in self._response_middleware:
                response = middleware_method(request, response)
            response = self.apply_response_fixes(request, response)
        except:  # Any exception should be gathered and handled
            signals.got_request_exception.send(sender=self.__class__, request=request)
            response = self.handle_uncaught_exception(request, resolver, sys.exc_info())

        response._closable_objects.append(request)

        return response

    def handle_uncaught_exception(self, request, resolver, exc_info):
        """
        Processing for any otherwise uncaught exceptions (those that will
        generate HTTP 500 responses). Can be overridden by subclasses who want
        customised 500 handling.

        Be *very* careful when overriding this because the error could be
        caused by anything, so assuming something like the database is always
        available would be an error.
        """
        if settings.DEBUG_PROPAGATE_EXCEPTIONS:
            raise

        logger.error('Internal Server Error: %s', request.path,
            exc_info=exc_info,
            extra={
                'status_code': 500,
                'request': request
            }
        )

        if settings.DEBUG:
            return debug.technical_500_response(request, *exc_info)

        # If Http500 handler is not installed, re-raise last exception
        if resolver.urlconf_module is None:
            six.reraise(*exc_info)
        # Return an HttpResponse that displays a friendly error message.
        callback, param_dict = resolver.resolve500()
        return callback(request, **param_dict)

    def apply_response_fixes(self, request, response):
        """
        Applies each of the functions in self.response_fixes to the request and
        response, modifying the response in the process. Returns the new
        response.
        """
        for func in self.response_fixes:
            response = func(request, response)
        return response
