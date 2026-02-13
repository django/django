from asgiref.sync import iscoroutinefunction

from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.test import SimpleTestCase
from django.views.decorators.gzip import gzip_page


class GzipPageTests(SimpleTestCase):
    # Gzip ignores content that is too short.
    content = "Content " * 100

    def test_wrapped_sync_function_is_not_coroutine_function(self):
        def sync_view(request):
            return HttpResponse()

        wrapped_view = gzip_page(sync_view)
        self.assertIs(iscoroutinefunction(wrapped_view), False)

    def test_wrapped_async_function_is_coroutine_function(self):
        async def async_view(request):
            return HttpResponse()

        wrapped_view = gzip_page(async_view)
        self.assertIs(iscoroutinefunction(wrapped_view), True)

    def test_gzip_page_decorator(self):
        @gzip_page
        def sync_view(request):
            return HttpResponse(content=self.content)

        request = HttpRequest()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip"
        response = sync_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Encoding"), "gzip")

    async def test_gzip_page_decorator_async_view(self):
        @gzip_page
        async def async_view(request):
            return HttpResponse(content=self.content)

        request = HttpRequest()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip"
        response = await async_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Encoding"), "gzip")

    def test_streaming_response_yields_chunks_incrementally(self):
        @gzip_page
        def stream_view(request):
            return StreamingHttpResponse(self.content.encode() for _ in range(5))

        request = HttpRequest()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip"
        response = stream_view(request)
        compressed_chunks = list(response)
        # Each input chunk should produce compressed output, not buffer
        # everything into a single chunk.
        self.assertGreater(len(compressed_chunks), 2)
