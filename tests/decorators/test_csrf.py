from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.views.decorators.csrf import csrf_exempt


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
