from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import modify_settings, override_settings
from django.utils.csp import CSP
from django.utils.translation import gettext as _

from .base import PlaywrightTestCase

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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Track CSP violations via SecurityPolicyViolationEvent.
        cls._csp_violations = []
        cls._browser_context.expose_function(
            "cspviolation",
            lambda violation: cls._csp_violations.append(violation),
        )
        cls._browser_context.add_init_script("""
            document.addEventListener('securitypolicyviolation', (e) => {
                window.cspviolation({
                    blockedURI: e.blockedURI,
                    violatedDirective: e.violatedDirective,
                    effectiveDirective: e.effectiveDirective,
                    originalPolicy: e.originalPolicy,
                    documentURI: e.documentURI,
                });
            });
        """)

    def tearDown(self):
        try:
            # WebKit injects inline style during screenshot(), which triggers
            # a style-src-elem CSP violation.
            violations = [
                violation
                for violation in self._csp_violations
                if not (
                    self.browser == "webkit"
                    and violation["effectiveDirective"] == "style-src-elem"
                    and violation["blockedURI"] == "inline"
                )
            ]
            # Ensure that no CSP violations were logged in the browser.
            self.assertEqual(violations, [])
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
        self.page.get_by_role("button", name=login_text).click()
        self.page.wait_for_url(f"{self.live_server_url}{login_url}")

    def click_and_expect_popup_to_close(self, locator):
        """
        Click a button that closes the popup and wait until the popup is
        closed.
        """
        from playwright.sync_api import Error

        popup = locator.page
        with popup.expect_event("close"):
            try:
                locator.click(no_wait_after=True)
            except Error:
                # The popup may close before Playwright finishes the click.
                # See https://github.com/microsoft/playwright/issues/26900
                if not popup.is_closed():
                    raise

    def _assertOptionsValues(self, options_selector, values):
        options = self.page.locator(options_selector)
        if values:
            actual_values = []
            for option in options.all():
                actual_values.append(option.get_attribute("value"))
            self.assertEqual(values, actual_values)
        else:
            # Wait until no options match the selector, as expected after a
            # DOM update that clears the <select>.
            self.expect(options).to_have_count(0)

    def assertSelectOptions(self, selector, values):
        """
        Assert that the <SELECT> widget identified by `selector` has the
        options with the given `values`.
        """
        self._assertOptionsValues("%s > option" % selector, values)

    def assertSelectedOptions(self, selector, values):
        """
        Assert that the <SELECT> widget identified by `selector` has the
        selected options with the given `values`.
        """
        self._assertOptionsValues("%s > option:checked" % selector, values)
