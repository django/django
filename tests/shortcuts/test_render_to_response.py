from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.test.utils import require_jinja2
from django.utils.deprecation import RemovedInDjango30Warning


@ignore_warnings(category=RemovedInDjango30Warning)
@override_settings(ROOT_URLCONF='shortcuts.urls')
class RenderToResponseTests(SimpleTestCase):

    def test_render_to_response(self):
        response = self.client.get('/render_to_response/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'FOO.BAR..\n')
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')

    def test_render_to_response_with_multiple_templates(self):
        response = self.client.get('/render_to_response/multiple_templates/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'FOO.BAR..\n')

    def test_render_to_response_with_content_type(self):
        response = self.client.get('/render_to_response/content_type/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'FOO.BAR..\n')
        self.assertEqual(response['Content-Type'], 'application/x-rendertest')

    def test_render_to_response_with_status(self):
        response = self.client.get('/render_to_response/status/')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b'FOO.BAR..\n')

    @require_jinja2
    def test_render_to_response_with_using(self):
        response = self.client.get('/render_to_response/using/')
        self.assertEqual(response.content, b'DTL\n')
        response = self.client.get('/render_to_response/using/?using=django')
        self.assertEqual(response.content, b'DTL\n')
        response = self.client.get('/render_to_response/using/?using=jinja2')
        self.assertEqual(response.content, b'Jinja2\n')
