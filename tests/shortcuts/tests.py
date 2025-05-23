from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.http.response import HttpResponseRedirectBase
from django.shortcuts import delayed_redirect, redirect, redirect_with_message
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.test.utils import require_jinja2


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


TEMPLATE_STRING = """
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="{{ delay }};url={{ url }}">
</head>
<body>
    <p>Redirecting to {{ url }} in {{ delay }} seconds.</p>
</body>
</html>
"""


@override_settings(
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": False,
            "OPTIONS": {
                "loaders": [
                    (
                        "django.template.loaders.locmem.Loader",
                        {
                            "delayed_redirect.html": TEMPLATE_STRING,
                        },
                    )
                ],
            },
        }
    ]
)
class DelayedRedirectTests(TestCase):
    def test_delayed_redirect_renders_correct_html(self):
        factory = RequestFactory()
        request = factory.get("/")
        response = delayed_redirect(request, "/next/", delay=7)

        self.assertContains(
            response, 'meta http-equiv="refresh" content="7;url=/next/"'
        )
        self.assertContains(response, "Redirecting to /next/ in 7 seconds.")


class RedirectWithMessageTests(TestCase):
    def test_redirect_with_message_sets_message(self):
        factory = RequestFactory()
        request = factory.get("/")

        setattr(request, "session", {})
        messages_storage = FallbackStorage(request)
        setattr(request, "_messages", messages_storage)

        response = redirect_with_message(
            request, "/success/", "Done!", msg_type="success"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/success/")

        stored_messages = list(request._messages)
        self.assertEqual(len(stored_messages), 1)
        self.assertEqual(stored_messages[0].message, "Done!")
        self.assertEqual(stored_messages[0].level, messages.SUCCESS)
