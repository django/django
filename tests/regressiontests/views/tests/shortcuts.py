from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings

@override_settings(
    TEMPLATE_CONTEXT_PROCESSORS=('django.core.context_processors.static',),
    STATIC_URL='/path/to/static/media/',
)
class ShortcutTests(TestCase):
    urls = 'regressiontests.views.generic_urls'

    def test_render_to_response(self):
        response = self.client.get('/shortcuts/render_to_response/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'FOO.BAR..\n')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_render_to_response_with_request_context(self):
        response = self.client.get('/shortcuts/render_to_response/request_context/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'FOO.BAR../path/to/static/media/\n')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_render_to_response_with_mimetype(self):
        response = self.client.get('/shortcuts/render_to_response/mimetype/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'FOO.BAR..\n')
        self.assertEqual(response['Content-Type'], 'application/x-rendertest')

    def test_render(self):
        response = self.client.get('/shortcuts/render/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'FOO.BAR../path/to/static/media/\n')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(response.context.current_app, None)

    def test_render_with_base_context(self):
        response = self.client.get('/shortcuts/render/base_context/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'FOO.BAR..\n')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_render_with_content_type(self):
        response = self.client.get('/shortcuts/render/content_type/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'FOO.BAR../path/to/static/media/\n')
        self.assertEqual(response['Content-Type'], 'application/x-rendertest')

    def test_render_with_status(self):
        response = self.client.get('/shortcuts/render/status/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, 'FOO.BAR../path/to/static/media/\n')

    def test_render_with_current_app(self):
        response = self.client.get('/shortcuts/render/current_app/')
        self.assertEqual(response.context.current_app, "foobar_app")

    def test_render_with_current_app_conflict(self):
        self.assertRaises(ValueError, self.client.get, '/shortcuts/render/current_app_conflict/')
