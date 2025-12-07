from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse
from django.test import SimpleTestCase
from django.views.decorators.common import no_append_slash


class NoAppendSlashTests(SimpleTestCase):
    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = no_append_slash(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = no_append_slash(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_no_append_slash_decorator(self):
        @no_append_slash
        def sync_view(request):
            return HttpResponse()

        self.assertIs(sync_view.should_append_slash, False)
        self.assertIsInstance(sync_view(HttpRequest()), HttpResponse)

    async def test_no_append_slash_decorator_async_view(self):
        @no_append_slash
        async def async_view(request):
            return HttpResponse()

        self.assertIs(async_view.should_append_slash, False)
        self.assertIsInstance(await async_view(HttpRequest()), HttpResponse)
