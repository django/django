from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.test import SimpleTestCase
from django.views.decorators.clickjacking import (
    xframe_options_deny,
    xframe_options_exempt,
    xframe_options_sameorigin,
)


class XFrameOptionsDenyTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = xframe_options_deny(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = xframe_options_deny(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_decorator_sets_x_frame_options_to_deny(self):
        @xframe_options_deny
        def a_view(request):
            return HttpResponse()

        response = a_view(HttpRequest())
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    async def test_decorator_sets_x_frame_options_to_deny_async_view(self):
        @xframe_options_deny
        async def an_async_view(request):
            return HttpResponse()

        response = await an_async_view(HttpRequest())
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")


class XFrameOptionsSameoriginTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = xframe_options_sameorigin(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = xframe_options_sameorigin(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_decorator_sets_x_frame_options_to_sameorigin(self):
        @xframe_options_sameorigin
        def a_view(request):
            return HttpResponse()

        response = a_view(HttpRequest())
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")

    async def test_decorator_sets_x_frame_options_to_sameorigin_async_view(self):
        @xframe_options_sameorigin
        async def an_async_view(request):
            return HttpResponse()

        response = await an_async_view(HttpRequest())
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")


class XFrameOptionsExemptTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = xframe_options_exempt(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = xframe_options_exempt(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_decorator_stops_x_frame_options_being_set(self):
        """
        @xframe_options_exempt instructs the XFrameOptionsMiddleware to NOT set
        the header.
        """

        @xframe_options_exempt
        def a_view(request):
            return HttpResponse()

        request = HttpRequest()
        response = a_view(request)
        self.assertIsNone(response.get("X-Frame-Options", None))
        self.assertIs(response.xframe_options_exempt, True)

        # The real purpose of the exempt decorator is to suppress the
        # middleware's functionality.
        middleware_response = XFrameOptionsMiddleware(a_view)(request)
        self.assertIsNone(middleware_response.get("X-Frame-Options"))

    async def test_exempt_decorator_async_view(self):
        @xframe_options_exempt
        async def an_async_view(request):
            return HttpResponse()

        request = HttpRequest()
        response = await an_async_view(request)
        self.assertIsNone(response.get("X-Frame-Options"))
        self.assertIs(response.xframe_options_exempt, True)

        # The real purpose of the exempt decorator is to suppress the
        # middleware's functionality.
        middleware_response = await XFrameOptionsMiddleware(an_async_view)(request)
        self.assertIsNone(middleware_response.get("X-Frame-Options"))
