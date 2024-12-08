from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.views.decorators.vary import vary_on_cookie, vary_on_headers


class VaryOnHeadersTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = vary_on_headers()(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = vary_on_headers()(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_vary_on_headers_decorator(self):
        @vary_on_headers("Header", "Another-header")
        def sync_view(request):
            return HttpResponse()

        response = sync_view(HttpRequest())
        self.assertEqual(response.get("Vary"), "Header, Another-header")

    async def test_vary_on_headers_decorator_async_view(self):
        @vary_on_headers("Header", "Another-header")
        async def async_view(request):
            return HttpResponse()

        response = await async_view(HttpRequest())
        self.assertEqual(response.get("Vary"), "Header, Another-header")


class VaryOnCookieTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = vary_on_cookie(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = vary_on_cookie(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_vary_on_cookie_decorator(self):
        @vary_on_cookie
        def sync_view(request):
            return HttpResponse()

        response = sync_view(HttpRequest())
        self.assertEqual(response.get("Vary"), "Cookie")

    async def test_vary_on_cookie_decorator_async_view(self):
        @vary_on_cookie
        async def async_view(request):
            return HttpResponse()

        response = await async_view(HttpRequest())
        self.assertEqual(response.get("Vary"), "Cookie")
