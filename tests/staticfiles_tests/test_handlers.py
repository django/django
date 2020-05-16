from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.handlers.asgi import ASGIHandler
from django.test import AsyncRequestFactory, SimpleTestCase, modify_settings


class TestASGIStaticFilesHandler(SimpleTestCase):
    async_request_factory = AsyncRequestFactory()

    @modify_settings(INSTALLED_APPS={'append': 'staticfiles_tests.apps.test'})
    async def test_get_async_response(self):
        request = self.async_request_factory.get('/static/test/file.txt')
        handler = ASGIStaticFilesHandler(ASGIHandler())
        response = await handler.get_response_async(request)
        response.close()
        self.assertEqual(response.status_code, 200)
