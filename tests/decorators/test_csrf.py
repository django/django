from asgiref.sync import iscoroutinefunction

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.views.decorators.csrf import (
    csrf_exempt,
    csrf_protect,
    ensure_csrf_cookie,
    requires_csrf_token,
)

CSRF_TOKEN = "1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD"


class CsrfTestMixin:
    def get_request(self, token=CSRF_TOKEN):
        request = HttpRequest()
        request.method = "POST"
        if token:
            request.POST["csrfmiddlewaretoken"] = token
            request.COOKIES[settings.CSRF_COOKIE_NAME] = token
        return request


class CsrfProtectTests(CsrfTestMixin, SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = csrf_protect(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = csrf_protect(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_csrf_protect_decorator(self):
        @csrf_protect
        def sync_view(request):
            return HttpResponse()

        request = self.get_request()
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(request.csrf_processing_done, True)

        with self.assertLogs("django.security.csrf", "WARNING"):
            request = self.get_request(token=None)
            response = sync_view(request)
            self.assertEqual(response.status_code, 403)

    async def test_csrf_protect_decorator_async_view(self):
        @csrf_protect
        async def async_view(request):
            return HttpResponse()

        request = self.get_request()
        response = await async_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(request.csrf_processing_done, True)

        with self.assertLogs("django.security.csrf", "WARNING"):
            request = self.get_request(token=None)
            response = await async_view(request)
            self.assertEqual(response.status_code, 403)


class RequiresCsrfTokenTests(CsrfTestMixin, SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = requires_csrf_token(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = requires_csrf_token(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_requires_csrf_token_decorator(self):
        @requires_csrf_token
        def sync_view(request):
            return HttpResponse()

        request = self.get_request()
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(request.csrf_processing_done, True)

        with self.assertNoLogs("django.security.csrf", "WARNING"):
            request = self.get_request(token=None)
            response = sync_view(request)
            self.assertEqual(response.status_code, 200)

    async def test_requires_csrf_token_decorator_async_view(self):
        @requires_csrf_token
        async def async_view(request):
            return HttpResponse()

        request = self.get_request()
        response = await async_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(request.csrf_processing_done, True)

        with self.assertNoLogs("django.security.csrf", "WARNING"):
            request = self.get_request(token=None)
            response = await async_view(request)
            self.assertEqual(response.status_code, 200)


class EnsureCsrfCookieTests(CsrfTestMixin, SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = ensure_csrf_cookie(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = ensure_csrf_cookie(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_ensure_csrf_cookie_decorator(self):
        @ensure_csrf_cookie
        def sync_view(request):
            return HttpResponse()

        request = self.get_request()
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(request.csrf_processing_done, True)

        with self.assertNoLogs("django.security.csrf", "WARNING"):
            request = self.get_request(token=None)
            response = sync_view(request)
            self.assertEqual(response.status_code, 200)

    async def test_ensure_csrf_cookie_decorator_async_view(self):
        @ensure_csrf_cookie
        async def async_view(request):
            return HttpResponse()

        request = self.get_request()
        response = await async_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIs(request.csrf_processing_done, True)

        with self.assertNoLogs("django.security.csrf", "WARNING"):
            request = self.get_request(token=None)
            response = await async_view(request)
            self.assertEqual(response.status_code, 200)


class CsrfExemptTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = csrf_exempt(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = csrf_exempt(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_csrf_exempt_decorator(self):
        @csrf_exempt
        def sync_view(request):
            return HttpResponse()

        self.assertIs(sync_view.csrf_exempt, True)
        self.assertIsInstance(sync_view(HttpRequest()), HttpResponse)

    async def test_csrf_exempt_decorator_async_view(self):
        @csrf_exempt
        async def async_view(request):
            return HttpResponse()

        self.assertIs(async_view.csrf_exempt, True)
        self.assertIsInstance(await async_view(HttpRequest()), HttpResponse)
