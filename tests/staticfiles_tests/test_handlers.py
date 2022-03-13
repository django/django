from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.handlers.asgi import ASGIHandler
from django.test import AsyncRequestFactory

from .cases import StaticFilesTestCase


class TestASGIStaticFilesHandler(StaticFilesTestCase):
    async_request_factory = AsyncRequestFactory()

    async def test_get_async_response(self):
        request = self.async_request_factory.get("/static/test/file.txt")
        handler = ASGIStaticFilesHandler(ASGIHandler())
        response = await handler.get_response_async(request)
        response.close()
        self.assertEqual(response.status_code, 200)

    async def test_get_async_response_not_found(self):
        request = self.async_request_factory.get("/static/test/not-found.txt")
        handler = ASGIStaticFilesHandler(ASGIHandler())
        response = await handler.get_response_async(request)
        self.assertEqual(response.status_code, 404)
