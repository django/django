from django.core.exceptions import DisallowedRedirect
from django.http.response import HttpResponseRedirectBase
from django.shortcuts import redirect
from django.test import SimpleTestCase, override_settings
from django.test.utils import require_jinja2
from django.utils.http import MAX_URL_REDIRECT_LENGTH


@override_settings(ROOT_URLCONF="shortcuts.urls")
class RenderTests(SimpleTestCase):
    def test_render(self):
        response = self.client.get("/render/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"FOO.BAR../render/\n")
        self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertFalse(hasattr(response.context.request, "current_app"))

    def test_render_with_multiple_templates(self):
        response = self.client.get("/render/multiple_templates/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"FOO.BAR../render/multiple_templates/\n")

    def test_render_with_content_type(self):
        response = self.client.get("/render/content_type/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"FOO.BAR../render/content_type/\n")
        self.assertEqual(response.headers["Content-Type"], "application/x-rendertest")

    def test_render_with_status(self):
        response = self.client.get("/render/status/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b"FOO.BAR../render/status/\n")

    @require_jinja2
    def test_render_with_using(self):
        response = self.client.get("/render/using/")
        self.assertEqual(response.content, b"DTL\n")
        response = self.client.get("/render/using/?using=django")
        self.assertEqual(response.content, b"DTL\n")
        response = self.client.get("/render/using/?using=jinja2")
        self.assertEqual(response.content, b"Jinja2\n")


class RedirectTests(SimpleTestCase):
    def test_redirect_response_status_code(self):
        tests = [
            (True, False, 301),
            (False, False, 302),
            (False, True, 307),
            (True, True, 308),
        ]
        for permanent, preserve_request, expected_status_code in tests:
            with self.subTest(permanent=permanent, preserve_request=preserve_request):
                response = redirect(
                    "/path/is/irrelevant/",
                    permanent=permanent,
                    preserve_request=preserve_request,
                )
                self.assertIsInstance(response, HttpResponseRedirectBase)
                self.assertEqual(response.status_code, expected_status_code)

    def test_redirect_max_length_default_raises(self):
        long_url = "https://example.com/" + "x" * MAX_URL_REDIRECT_LENGTH
        msg = f"Unsafe redirect exceeding {MAX_URL_REDIRECT_LENGTH} characters"
        with self.assertRaisesMessage(DisallowedRedirect, msg):
            redirect(long_url)

    def test_redirect_max_length_override_passes(self):
        long_url = "https://example.com/" + "x" * MAX_URL_REDIRECT_LENGTH
        response = redirect(long_url, max_length=None)
        self.assertEqual(response.url, long_url)

    def test_redirect_custom_strict_limit_raises(self):
        msg = "Unsafe redirect exceeding 5 characters"
        with self.assertRaisesMessage(DisallowedRedirect, msg):
            redirect("https://example.com/", max_length=5)
