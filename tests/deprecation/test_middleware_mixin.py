import asyncio
import threading

from asgiref.sync import async_to_sync

from django.contrib.admindocs.middleware import XViewMiddleware
from django.contrib.auth.middleware import (
    AuthenticationMiddleware, RemoteUserMiddleware,
)
from django.contrib.flatpages.middleware import FlatpageFallbackMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sites.middleware import CurrentSiteMiddleware
from django.db import connection
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.middleware.cache import (
    CacheMiddleware, FetchFromCacheMiddleware, UpdateCacheMiddleware,
)
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.middleware.common import (
    BrokenLinkEmailsMiddleware, CommonMiddleware,
)
from django.middleware.csrf import CsrfViewMiddleware
from django.middleware.gzip import GZipMiddleware
from django.middleware.http import ConditionalGetMiddleware
from django.middleware.locale import LocaleMiddleware
from django.middleware.security import SecurityMiddleware
from django.test import SimpleTestCase
from django.utils.deprecation import MiddlewareMixin, RemovedInDjango40Warning


class MiddlewareMixinTests(SimpleTestCase):
    """
    Deprecation warning is raised when using get_response=None.
    """
    msg = 'Passing None for the middleware get_response argument is deprecated.'
    middlewares = [
        AuthenticationMiddleware,
        BrokenLinkEmailsMiddleware,
        CacheMiddleware,
        CommonMiddleware,
        ConditionalGetMiddleware,
        CsrfViewMiddleware,
        CurrentSiteMiddleware,
        FetchFromCacheMiddleware,
        FlatpageFallbackMiddleware,
        GZipMiddleware,
        LocaleMiddleware,
        MessageMiddleware,
        RedirectFallbackMiddleware,
        RemoteUserMiddleware,
        SecurityMiddleware,
        SessionMiddleware,
        UpdateCacheMiddleware,
        XFrameOptionsMiddleware,
        XViewMiddleware,
    ]

    def test_deprecation(self):
        for middleware in self.middlewares:
            with self.subTest(middleware=middleware):
                with self.assertRaisesMessage(RemovedInDjango40Warning, self.msg):
                    middleware()

    def test_passing_explicit_none(self):
        for middleware in self.middlewares:
            with self.subTest(middleware=middleware):
                with self.assertRaisesMessage(RemovedInDjango40Warning, self.msg):
                    middleware(None)

    def test_coroutine(self):
        async def async_get_response(request):
            return HttpResponse()

        def sync_get_response(request):
            return HttpResponse()

        for middleware in self.middlewares:
            with self.subTest(middleware=middleware.__qualname__):
                # Middleware appears as coroutine if get_function is
                # a coroutine.
                middleware_instance = middleware(async_get_response)
                self.assertIs(asyncio.iscoroutinefunction(middleware_instance), True)
                # Middleware doesn't appear as coroutine if get_function is not
                # a coroutine.
                middleware_instance = middleware(sync_get_response)
                self.assertIs(asyncio.iscoroutinefunction(middleware_instance), False)

    def test_sync_to_async_uses_base_thread_and_connection(self):
        """
        The process_request() and process_response() hooks must be called with
        the sync_to_async thread_sensitive flag enabled, so that database
        operations use the correct thread and connection.
        """
        def request_lifecycle():
            """Fake request_started/request_finished."""
            return (threading.get_ident(), id(connection))

        async def get_response(self):
            return HttpResponse()

        class SimpleMiddleWare(MiddlewareMixin):
            def process_request(self, request):
                request.thread_and_connection = request_lifecycle()

            def process_response(self, request, response):
                response.thread_and_connection = request_lifecycle()
                return response

        threads_and_connections = []
        threads_and_connections.append(request_lifecycle())

        request = HttpRequest()
        response = async_to_sync(SimpleMiddleWare(get_response))(request)
        threads_and_connections.append(request.thread_and_connection)
        threads_and_connections.append(response.thread_and_connection)

        threads_and_connections.append(request_lifecycle())

        self.assertEqual(len(threads_and_connections), 4)
        self.assertEqual(len(set(threads_and_connections)), 1)
