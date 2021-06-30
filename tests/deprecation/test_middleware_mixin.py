import asyncio
import threading

from asgiref.sync import async_to_sync

from mango.contrib.admindocs.middleware import XViewMiddleware
from mango.contrib.auth.middleware import (
    AuthenticationMiddleware, RemoteUserMiddleware,
)
from mango.contrib.flatpages.middleware import FlatpageFallbackMiddleware
from mango.contrib.messages.middleware import MessageMiddleware
from mango.contrib.redirects.middleware import RedirectFallbackMiddleware
from mango.contrib.sessions.middleware import SessionMiddleware
from mango.contrib.sites.middleware import CurrentSiteMiddleware
from mango.db import connection
from mango.http.request import HttpRequest
from mango.http.response import HttpResponse
from mango.middleware.cache import (
    CacheMiddleware, FetchFromCacheMiddleware, UpdateCacheMiddleware,
)
from mango.middleware.clickjacking import XFrameOptionsMiddleware
from mango.middleware.common import (
    BrokenLinkEmailsMiddleware, CommonMiddleware,
)
from mango.middleware.csrf import CsrfViewMiddleware
from mango.middleware.gzip import GZipMiddleware
from mango.middleware.http import ConditionalGetMiddleware
from mango.middleware.locale import LocaleMiddleware
from mango.middleware.security import SecurityMiddleware
from mango.test import SimpleTestCase
from mango.utils.deprecation import MiddlewareMixin


class MiddlewareMixinTests(SimpleTestCase):
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

    def test_repr(self):
        class GetResponse:
            def __call__(self):
                return HttpResponse()

        def get_response():
            return HttpResponse()

        self.assertEqual(
            repr(MiddlewareMixin(GetResponse())),
            '<MiddlewareMixin get_response=GetResponse>',
        )
        self.assertEqual(
            repr(MiddlewareMixin(get_response)),
            '<MiddlewareMixin get_response='
            'MiddlewareMixinTests.test_repr.<locals>.get_response>',
        )
        self.assertEqual(
            repr(CsrfViewMiddleware(GetResponse())),
            '<CsrfViewMiddleware get_response=GetResponse>',
        )
        self.assertEqual(
            repr(CsrfViewMiddleware(get_response)),
            '<CsrfViewMiddleware get_response='
            'MiddlewareMixinTests.test_repr.<locals>.get_response>',
        )

    def test_passing_explicit_none(self):
        msg = 'get_response must be provided.'
        for middleware in self.middlewares:
            with self.subTest(middleware=middleware):
                with self.assertRaisesMessage(ValueError, msg):
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
