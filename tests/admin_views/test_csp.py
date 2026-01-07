from django.test import TestCase, override_settings
from django.urls import reverse

# ---------------------------------------------------------------------
# Reusable middleware stacks (important for admin!)
# ---------------------------------------------------------------------

BASE_MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CSP_MIDDLEWARE = BASE_MIDDLEWARE + [
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
]


# ---------------------------------------------------------------------
# Test case
# ---------------------------------------------------------------------


@override_settings(
    ROOT_URLCONF="admin_views.urls",
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ],
    MIDDLEWARE=BASE_MIDDLEWARE,
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        },
    ],
)
class AdminCSPNonceTests(TestCase):
    """
    Regression tests for CSP nonce behavior in Django admin templates.

    We intentionally test ONLY whether the nonce appears in HTML.
    CSP headers are tested elsewhere in Django.
    """

    def get_admin_index(self):
        return self.client.get(reverse("admin:index"), follow=True)

    def assert_no_nonce(self, response):
        self.assertNotIn(
            'nonce="',
            response.content.decode(),
            msg="Nonce unexpectedly rendered in admin HTML",
        )

    def assert_has_nonce(self, response):
        self.assertIn(
            'nonce="',
            response.content.decode(),
            msg="Expected nonce not rendered in admin HTML",
        )

    # ------------------------------------------------------------------
    # 1. CSP middleware NOT enabled
    # ------------------------------------------------------------------

    def test_admin_without_csp_middleware(self):
        """
        CSP disabled → no nonce rendered.
        """
        response = self.get_admin_index()
        self.assert_no_nonce(response)

    # ------------------------------------------------------------------
    # 2. CSP enabled WITH nonces
    # ------------------------------------------------------------------

    @override_settings(
        MIDDLEWARE=CSP_MIDDLEWARE,
        CONTENT_SECURITY_POLICY={
            "DIRECTIVES": {
                "script-src": ["'self'", "nonce"],
            }
        },
    )
    def test_admin_with_csp_nonces(self):
        """
        CSP nonces enabled → nonce rendered in admin HTML.
        """
        response = self.get_admin_index()
        self.assert_has_nonce(response)

    # ------------------------------------------------------------------
    # 3. CSP enabled WITH nonces + strict-dynamic
    # ------------------------------------------------------------------

    @override_settings(
        MIDDLEWARE=CSP_MIDDLEWARE,
        CONTENT_SECURITY_POLICY={
            "DIRECTIVES": {
                "script-src": ["'self'", "nonce", "'strict-dynamic'"],
            }
        },
    )
    def test_admin_with_csp_nonces_and_strict_dynamic(self):
        """
        strict-dynamic must not prevent nonce rendering.
        """
        response = self.get_admin_index()
        self.assert_has_nonce(response)
