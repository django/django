"""
Tests for Django's bundled context processors.
"""

from django.test import SimpleTestCase, TestCase, modify_settings, override_settings
from django.utils.csp import CSP


@override_settings(
    ROOT_URLCONF="context_processors.urls",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.request",
                ],
            },
        }
    ],
)
class RequestContextProcessorTests(SimpleTestCase):
    """
    Tests for the ``django.template.context_processors.request`` processor.
    """

    def test_request_attributes(self):
        """
        The request object is available in the template and that its
        attributes can't be overridden by GET and POST parameters (#3828).
        """
        url = "/request_attrs/"
        # We should have the request object in the template.
        response = self.client.get(url)
        self.assertContains(response, "Have request")
        # Test is_secure.
        response = self.client.get(url)
        self.assertContains(response, "Not secure")
        response = self.client.get(url, {"is_secure": "blah"})
        self.assertContains(response, "Not secure")
        response = self.client.post(url, {"is_secure": "blah"})
        self.assertContains(response, "Not secure")
        # Test path.
        response = self.client.get(url)
        self.assertContains(response, url)
        response = self.client.get(url, {"path": "/blah/"})
        self.assertContains(response, url)
        response = self.client.post(url, {"path": "/blah/"})
        self.assertContains(response, url)


@override_settings(
    DEBUG=True,
    INTERNAL_IPS=["127.0.0.1"],
    ROOT_URLCONF="context_processors.urls",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                ],
            },
        }
    ],
)
class DebugContextProcessorTests(TestCase):
    """
    Tests for the ``django.template.context_processors.debug`` processor.
    """

    databases = {"default", "other"}

    def test_debug(self):
        url = "/debug/"
        # We should have the debug flag in the template.
        response = self.client.get(url)
        self.assertContains(response, "Have debug")

        # And now we should not
        with override_settings(DEBUG=False):
            response = self.client.get(url)
            self.assertNotContains(response, "Have debug")

    def test_sql_queries(self):
        """
        Test whether sql_queries represents the actual amount
        of queries executed. (#23364)
        """
        url = "/debug/"
        response = self.client.get(url)
        self.assertContains(response, "First query list: 0")
        self.assertContains(response, "Second query list: 1")
        # Check we have not actually memoized connection.queries
        self.assertContains(response, "Third query list: 2")
        # Check queries for DB connection 'other'
        self.assertContains(response, "Fourth query list: 3")


@override_settings(
    ROOT_URLCONF="context_processors.urls",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.csp",
                ],
            },
        }
    ],
    MIDDLEWARE=[
        "django.middleware.csp.ContentSecurityPolicyMiddleware",
    ],
    SECURE_CSP={
        "script-src": [CSP.SELF, CSP.NONCE],
    },
)
class CSPContextProcessorTests(TestCase):
    """
    Tests for the django.template.context_processors.csp_nonce processor.
    """

    def test_csp_nonce_in_context(self):
        response = self.client.get("/csp_nonce/")
        self.assertIn("csp_nonce", response.context)

    @modify_settings(
        MIDDLEWARE={"remove": "django.middleware.csp.ContentSecurityPolicyMiddleware"}
    )
    def test_csp_nonce_in_context_no_middleware(self):
        response = self.client.get("/csp_nonce/")
        self.assertIn("csp_nonce", response.context)

    def test_csp_nonce_in_header(self):
        response = self.client.get("/csp_nonce/")
        self.assertIn(CSP.HEADER_ENFORCE, response.headers)
        csp_header = response.headers[CSP.HEADER_ENFORCE]
        nonce = response.context["csp_nonce"]
        self.assertIn(f"'nonce-{nonce}'", csp_header)

    def test_different_nonce_per_request(self):
        response1 = self.client.get("/csp_nonce/")
        response2 = self.client.get("/csp_nonce/")
        self.assertNotEqual(
            response1.context["csp_nonce"],
            response2.context["csp_nonce"],
        )

    def test_csp_nonce_in_template(self):
        response = self.client.get("/csp_nonce/")
        nonce = response.context["csp_nonce"]
        self.assertIn(f'<script nonce="{nonce}">', response.text)

    def test_csp_nonce_length(self):
        response = self.client.get("/csp_nonce/")
        nonce = response.context["csp_nonce"]
        self.assertEqual(len(nonce), 22)  # Based on secrets.token_urlsafe of 16 bytes.
