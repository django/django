from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import modify_settings, override_settings
from django.test.playwright import PlaywrightTestCase
from django.utils.csp import CSP
from django.utils.translation import gettext as _

# Make unittest ignore frames in this module when reporting failures.
__unittest = True


@modify_settings(
    MIDDLEWARE={"append": "django.middleware.csp.ContentSecurityPolicyMiddleware"}
)
@override_settings(
    SECURE_CSP={
        "default-src": [CSP.NONE],
        "connect-src": [CSP.SELF],
        "img-src": [CSP.SELF],
        "script-src": [CSP.SELF],
        "style-src": [CSP.SELF],
    },
)
class AdminPlaywrightTestCase(PlaywrightTestCase, StaticLiveServerTestCase):
    available_apps = [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.sites",
    ]

    def tearDown(self):
        try:
            # Ensure that no CSP violations were logged in the browser.
            self.assertEqual(self._csp_violations, [])
        finally:
            self._csp_violations.clear()
            super().tearDown()

    def admin_login(self, username, password, login_url="/admin/"):
        """
        Log in to the admin.
        """
        self.page.goto(f"{self.live_server_url}{login_url}")
        self.page.locator('[name="username"]').fill(username)
        self.page.locator('[name="password"]').fill(password)
        login_text = _("Log in")
        self.page.locator(f'input[value="{login_text}"]').click()
        self.page.wait_for_url(f"{self.live_server_url}{login_url}")
