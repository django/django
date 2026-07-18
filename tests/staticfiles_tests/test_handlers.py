import threading

from asgiref.sync import sync_to_async

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.handlers.asgi import ASGIHandler
from django.http import HttpResponse
from django.test import AsyncRequestFactory, override_settings

from .cases import StaticFilesTestCase


class MockApplication:
    """ASGI application that returns a string indicating that it was called."""

    async def __call__(self, scope, receive, send):
        return "Application called"


error_handler_threads = {}


def log_thread(key):
    error_handler_threads[key] = threading.current_thread()


urlpatterns = []


def handler404(request, exception=None):
    log_thread("error_handler")
    return HttpResponse("Error handler content", status=404)


class TestASGIStaticFilesHandler(StaticFilesTestCase):
    async_request_factory = AsyncRequestFactory()

    async def test_get_async_response(self):
        request = self.async_request_factory.get("/static/test/file.txt")
        handler = ASGIStaticFilesHandler(ASGIHandler())
        response = await handler.get_response_async(request)
        response.close()
        self.assertEqual(response.status_code, 200)

    async def test_get_async_response_not_found(self):
        error_handler_threads.clear()
        await sync_to_async(log_thread)("worker")

        request = self.async_request_factory.get("/static/test/not-found.txt")
        handler = ASGIStaticFilesHandler(ASGIHandler())
        with override_settings(ROOT_URLCONF="staticfiles_tests.test_handlers"):
            response = await handler.get_response_async(request)
        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            error_handler_threads["error_handler"],
            error_handler_threads["worker"],
        )

    async def test_non_http_requests_passed_to_the_wrapped_application(self):
        tests = [
            "/static/path.txt",
            "/non-static/path.txt",
        ]
        for path in tests:
            with self.subTest(path=path):
                scope = {"type": "websocket", "path": path}
                handler = ASGIStaticFilesHandler(MockApplication())
                response = await handler(scope, None, None)
                self.assertEqual(response, "Application called")
