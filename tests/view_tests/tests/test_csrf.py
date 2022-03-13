from django.template import TemplateDoesNotExist
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.utils.translation import override
from django.views.csrf import CSRF_FAILURE_TEMPLATE_NAME, csrf_failure


@override_settings(ROOT_URLCONF="view_tests.urls")
class CsrfViewTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=True)

    @override_settings(
        USE_I18N=True,
        MIDDLEWARE=[
            "django.middleware.locale.LocaleMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
        ],
    )
    def test_translation(self):
        """An invalid request is rejected with a localized error message."""
        response = self.client.post("/")
        self.assertContains(response, "Forbidden", status_code=403)
        self.assertContains(
            response, "CSRF verification failed. Request aborted.", status_code=403
        )

        with self.settings(LANGUAGE_CODE="nl"), override("en-us"):
            response = self.client.post("/")
            self.assertContains(response, "Verboden", status_code=403)
            self.assertContains(
                response,
                "CSRF-verificatie mislukt. Verzoek afgebroken.",
                status_code=403,
            )

    @override_settings(SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_no_referer(self):
        """
        Referer header is strictly checked for POST over HTTPS. Trigger the
        exception by sending an incorrect referer.
        """
        response = self.client.post("/", HTTP_X_FORWARDED_PROTO="https")
        self.assertContains(
            response,
            "You are seeing this message because this HTTPS site requires a "
            "“Referer header” to be sent by your web browser, but "
            "none was sent.",
            status_code=403,
        )
        self.assertContains(
            response,
            "If you have configured your browser to disable “Referer” "
            "headers, please re-enable them, at least for this site, or for "
            "HTTPS connections, or for “same-origin” requests.",
            status_code=403,
        )
        self.assertContains(
            response,
            "If you are using the &lt;meta name=&quot;referrer&quot; "
            "content=&quot;no-referrer&quot;&gt; tag or including the "
            "“Referrer-Policy: no-referrer” header, please remove them.",
            status_code=403,
        )

    def test_no_cookies(self):
        """
        The CSRF cookie is checked for POST. Failure to send this cookie should
        provide a nice error message.
        """
        response = self.client.post("/")
        self.assertContains(
            response,
            "You are seeing this message because this site requires a CSRF "
            "cookie when submitting forms. This cookie is required for "
            "security reasons, to ensure that your browser is not being "
            "hijacked by third parties.",
            status_code=403,
        )

    @override_settings(TEMPLATES=[])
    def test_no_django_template_engine(self):
        """
        The CSRF view doesn't depend on the TEMPLATES configuration (#24388).
        """
        response = self.client.post("/")
        self.assertContains(response, "Forbidden", status_code=403)

    @override_settings(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "OPTIONS": {
                    "loaders": [
                        (
                            "django.template.loaders.locmem.Loader",
                            {
                                CSRF_FAILURE_TEMPLATE_NAME: (
                                    "Test template for CSRF failure"
                                )
                            },
                        ),
                    ],
                },
            }
        ]
    )
    def test_custom_template(self):
        """A custom CSRF_FAILURE_TEMPLATE_NAME is used."""
        response = self.client.post("/")
        self.assertContains(response, "Test template for CSRF failure", status_code=403)

    def test_custom_template_does_not_exist(self):
        """An exception is raised if a nonexistent template is supplied."""
        factory = RequestFactory()
        request = factory.post("/")
        with self.assertRaises(TemplateDoesNotExist):
            csrf_failure(request, template_name="nonexistent.html")
