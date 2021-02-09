import asyncio
import logging
import types

from asgiref.sync import async_to_sync, sync_to_async

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, MiddlewareNotUsed
from django.core.signals import request_finished
from django.db import connections, transaction
from django.urls import get_resolver, set_urlconf
from django.utils.log import log_response
from django.utils.module_loading import import_string

from .exception import convert_exception_to_response

logger = logging.getLogger('django.request')


class BaseHandler:
    _view_middleware = None
    _template_response_middleware = None
    _exception_middleware = None
    _middleware_chain = None

    def load_middleware(self, is_async=False):
        """
        Populate middleware lists from settings.MIDDLEWARE.

        Must be called after the environment is fixed (see __call__ in subclasses).
        """
        self._view_middleware = []
        self._template_response_middleware = []
        self._exception_middleware = []

        get_response = self._get_response_async if is_async else self._get_response
        handler = convert_exception_to_response(get_response)
        handler_is_async = is_async
        for middleware_path in reversed(settings.MIDDLEWARE):
            middleware = import_string(middleware_path)
            middleware_can_sync = getattr(middleware, 'sync_capable', True)
            middleware_can_async = getattr(middleware, 'async_capable', False)
            if not middleware_can_sync and not middleware_can_async:
                raise RuntimeError(
                    'Middleware %s must have at least one of '
                    'sync_capable/async_capable set to True.' % middleware_path
                )
            elif not handler_is_async and middleware_can_sync:
                middleware_is_async = False
            else:
                middleware_is_async = middleware_can_async
            try:
                # Adapt handler, if needed.
                adapted_handler = self.adapt_method_mode(
                    middleware_is_async, handler, handler_is_async,
                    debug=settings.DEBUG, name='middleware %s' % middleware_path,
                )
                mw_instance = middleware(adapted_handler)
            except MiddlewareNotUsed as exc:
                if settings.DEBUG:
                    if str(exc):
                        logger.debug('MiddlewareNotUsed(%r): %s', middleware_path, exc)
                    else:
                        logger.debug('MiddlewareNotUsed: %r', middleware_path)
                continue
            else:
                handler = adapted_handler

            if mw_instance is None:
                raise ImproperlyConfigured(
                    'Middleware factory %s returned None.' % middleware_path
                )

            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.insert(
                    0,
                    self.adapt_method_mode(is_async, mw_instance.process_view),
                )
            if hasattr(mw_instance, 'process_template_response'):
                self._template_response_middleware.append(
                    self.adapt_method_mode(is_async, mw_instance.process_template_response),
                )
            if hasattr(mw_instance, 'process_exception'):
                # The exception-handling stack is still always synchronous for
                # now, so adapt that way.
                self._exception_middleware.append(
                    self.adapt_method_mode(False, mw_instance.process_exception),
                )

            handler = convert_exception_to_response(mw_instance)
            handler_is_async = middleware_is_async

        # Adapt the top of the stack, if needed.
        handler = self.adapt_method_mode(is_async, handler, handler_is_async)
        # We only assign to this when initialization is complete as it is used
        # as a flag for initialization being complete.
        self._middleware_chain = handler

    def adapt_method_mode(
        self, is_async, method, method_is_async=None, debug=False, name=None,
    ):
        """
        Adapt a method to be in the correct "mode":
        - If is_async is False:
          - Synchronous methods are left alone
          - Asynchronous methods are wrapped with async_to_sync
        - If is_async is True:
          - Synchronous methods are wrapped with sync_to_async()
          - Asynchronous methods are left alone
        """
        if method_is_async is None:
            method_is_async = asyncio.iscoroutinefunction(method)
        if debug and not name:
            name = name or 'method %s()' % method.__qualname__
        if is_async:
            if not method_is_async:
                if debug:
                    logger.debug('Synchronous %s adapted.', name)
                return sync_to_async(method, thread_sensitive=True)
        elif method_is_async:
            if debug:
                logger.debug('Asynchronous %s adapted.', name)
            return async_to_sync(method)
        return method

    def get_response(self, request):
        """Return an HttpResponse object for the given HttpRequest."""
        # Setup default url resolver for this thread
        set_urlconf(settings.ROOT_URLCONF)
        response = self._middleware_chain(request)
        response._resource_closers.append(request.close)
        if response.status_code >= 400:
            log_response(
                '%s: %s', response.reason_phrase, request.path,
                response=response,
                request=request,
            )
        return response

    async def get_response_async(self, request):
        """
        Asynchronous version of get_response.

        Funneling everything, including WSGI, into a single async
        get_response() is too slow. Avoid the context switch by using
        a separate async response path.
        """
        # Setup default url resolver for this thread.
        set_urlconf(settings.ROOT_URLCONF)
        response = await self._middleware_chain(request)
        response._resource_closers.append(request.close)
        if response.status_code >= 400:
            await sync_to_async(log_response, thread_sensitive=False)(
                '%s: %s', response.reason_phrase, request.path,
                response=response,
                request=request,
            )
        return response

    def _get_response(self, request):
        """
        Resolve and call the view, then apply view, exception, and
        template_response middleware. This method is everything that happens
        inside the request/response middleware.
        """
        response = None
        callback, callback_args, callback_kwargs = self.resolve_request(request)

        # Apply view middleware
        for middleware_method in self._view_middleware:
            response = middleware_method(request, callback, callback_args, callback_kwargs)
            if response:
                break

        if response is None:
            wrapped_callback = self.make_view_atomic(callback)
            # If it is an asynchronous view, run it in a subthread.
            if asyncio.iscoroutinefunction(wrapped_callback):
                wrapped_callback = async_to_sync(wrapped_callback)
            try:
                response = wrapped_callback(request, *callback_args, **callback_kwargs)
            except Exception as e:
                response = self.process_exception_by_middleware(e, request)
                if response is None:
                    raise

        # Complain if the view returned None (a common error).
        self.check_response(response, callback)

        # If the response supports deferred rendering, apply template
        # response middleware and then render the response
        if hasattr(response, 'render') and callable(response.render):
            for middleware_method in self._template_response_middleware:
                response = middleware_method(request, response)
                # Complain if the template response middleware returned None (a common error).
                self.check_response(
                    response,
                    middleware_method,
                    name='%s.process_template_response' % (
                        middleware_method.__self__.__class__.__name__,
                    )
                )
            try:
                response = response.render()
            except Exception as e:
                response = self.process_exception_by_middleware(e, request)
                if response is None:
                    raise

        return response

    async def _get_response_async(self, request):
        """
        Resolve and call the view, then apply view, exception, and
        template_response middleware. This method is everything that happens
        inside the request/response middleware.
        """
        response = None
        callback, callback_args, callback_kwargs = self.resolve_request(request)

        # Apply view middleware.
        for middleware_method in self._view_middleware:
            response = await middleware_method(request, callback, callback_args, callback_kwargs)
            if response:
                break

        if response is None:
            wrapped_callback = self.make_view_atomic(callback)
            # If it is a synchronous view, run it in a subthread
            if not asyncio.iscoroutinefunction(wrapped_callback):
                wrapped_callback = sync_to_async(wrapped_callback, thread_sensitive=True)
            try:
                response = await wrapped_callback(request, *callback_args, **callback_kwargs)
            except Exception as e:
                response = await sync_to_async(
                    self.process_exception_by_middleware,
                    thread_sensitive=True,
                )(e, request)
                if response is None:
                    raise

        # Complain if the view returned None or an uncalled coroutine.
        self.check_response(response, callback)

        # If the response supports deferred rendering, apply template
        # response middleware and then render the response
        if hasattr(response, 'render') and callable(response.render):
            for middleware_method in self._template_response_middleware:
                response = await middleware_method(request, response)
                # Complain if the template response middleware returned None or
                # an uncalled coroutine.
                self.check_response(
                    response,
                    middleware_method,
                    name='%s.process_template_response' % (
                        middleware_method.__self__.__class__.__name__,
                    )
                )
            try:
                if asyncio.iscoroutinefunction(response.render):
                    response = await response.render()
                else:
                    response = await sync_to_async(response.render, thread_sensitive=True)()
            except Exception as e:
                response = await sync_to_async(
                    self.process_exception_by_middleware,
                    thread_sensitive=True,
                )(e, request)
                if response is None:
                    raise

        # Make sure the response is not a coroutine
        if asyncio.iscoroutine(response):
            raise RuntimeError('Response is still a coroutine.')
        return response

    def resolve_request(self, request):
        """
        Retrieve/set the urlconf for the request. Return the view resolved,
        with its args and kwargs.
        """
        # Work out the resolver.
        if hasattr(request, 'urlconf'):
            urlconf = request.urlconf
            set_urlconf(urlconf)
            resolver = get_resolver(urlconf)
        else:
            resolver = get_resolver()
        # Resolve the view, and assign the match object back to the request.
        resolver_match = resolver.resolve(request.path_info)
        request.resolver_match = resolver_match
        return resolver_match

    def check_response(self, response, callback, name=None):
        """
        Raise an error if the view returned None or an uncalled coroutine.
        """
        if not(response is None or asyncio.iscoroutine(response)):
            return
        if not name:
            if isinstance(callback, types.FunctionType):  # FBV
                name = 'The view %s.%s' % (callback.__module__, callback.__name__)
            else:  # CBV
                name = 'The view %s.%s.__call__' % (
                    callback.__module__,
                    callback.__class__.__name__,
                )
        if response is None:
            raise ValueError(
                "%s didn't return an HttpResponse object. It returned None "
                "instead." % name
            )
        elif asyncio.iscoroutine(response):
            raise ValueError(
                "%s didn't return an HttpResponse object. It returned an "
                "unawaited coroutine instead. You may need to add an 'await' "
                "into your view." % name
            )

    # Other utility methods.

    def make_view_atomic(self, view):
        non_atomic_requests = getattr(view, '_non_atomic_requests', set())
        for db in connections.all():
            if db.settings_dict['ATOMIC_REQUESTS'] and db.alias not in non_atomic_requests:
                if asyncio.iscoroutinefunction(view):
                    raise RuntimeError(
                        'You cannot use ATOMIC_REQUESTS with async views.'
                    )
                view = transaction.atomic(using=db.alias)(view)
        return view

    def process_exception_by_middleware(self, exception, request):
        """
        Pass the exception to the exception middleware. If no middleware
        return a response for this exception, return None.
        """
        for middleware_method in self._exception_middleware:
            response = middleware_method(request, exception)
            if response:
                return response
        return None


def reset_urlconf(sender, **kwargs):
    """Reset the URLconf after each request is finished."""
    set_urlconf(None)


request_finished.connect(reset_urlconf)
