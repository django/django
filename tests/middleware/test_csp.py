import time

from utils_tests.test_csp import basic_config, basic_policy

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import SimpleTestCase
from django.test.selenium import SeleniumTestCase
from django.test.utils import modify_settings, override_settings
from django.utils.csp import CSP

from .views import csp_reports


@override_settings(
    MIDDLEWARE=["django.middleware.csp.ContentSecurityPolicyMiddleware"],
    ROOT_URLCONF="middleware.urls",
)
class CSPMiddlewareTest(SimpleTestCase):
    @override_settings(SECURE_CSP=None, SECURE_CSP_REPORT_ONLY=None)
    def test_csp_defaults_off(self):
        response = self.client.get("/csp-base/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    @override_settings(SECURE_CSP=basic_config, SECURE_CSP_REPORT_ONLY=None)
    def test_csp_basic(self):
        """
        With SECURE_CSP set to a valid value, the middleware adds a
        "Content-Security-Policy" header to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    @override_settings(SECURE_CSP={"default-src": [CSP.SELF, CSP.NONCE]})
    def test_csp_basic_with_nonce(self):
        """
        Test the nonce is added to the header and matches what is in the view.
        """
        response = self.client.get("/csp-nonce/")
        nonce = response.text
        self.assertTrue(nonce)
        self.assertEqual(
            response[CSP.HEADER_ENFORCE], f"default-src 'self' 'nonce-{nonce}'"
        )

    @override_settings(SECURE_CSP={"default-src": [CSP.SELF, CSP.NONCE]})
    def test_csp_basic_with_nonce_but_unused(self):
        """
        Test if `request.csp_nonce` is never accessed, it is not added to the
        header.
        """
        response = self.client.get("/csp-base/")
        nonce = response.text
        self.assertIsNotNone(nonce)
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)

    @override_settings(SECURE_CSP=None, SECURE_CSP_REPORT_ONLY=basic_config)
    def test_csp_report_only_basic(self):
        """
        With SECURE_CSP_REPORT_ONLY set to a valid value, the middleware adds a
        "Content-Security-Policy-Report-Only" header to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)
        self.assertNotIn(CSP.HEADER_ENFORCE, response)

    @override_settings(
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_both(self):
        """
        If both SECURE_CSP and SECURE_CSP_REPORT_ONLY are set, the middleware
        adds both headers to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[CSP.HEADER_ENFORCE], basic_policy)
        self.assertEqual(response[CSP.HEADER_REPORT_ONLY], basic_policy)

    @override_settings(
        DEBUG=True,
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_404_debug_view(self):
        """
        Test that the CSP headers are not added to the debug view.
        """
        response = self.client.get("/csp-404/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)

    @override_settings(
        DEBUG=True,
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_500_debug_view(self):
        """
        Test that the CSP headers are not added to the debug view.
        """
        with self.assertLogs("django.request", "WARNING"):
            response = self.client.get("/csp-500/")
        self.assertNotIn(CSP.HEADER_ENFORCE, response)
        self.assertNotIn(CSP.HEADER_REPORT_ONLY, response)


@override_settings(
    ROOT_URLCONF="middleware.urls",
    SECURE_CSP_REPORT_ONLY={
        "default-src": [CSP.NONE],
        "img-src": [CSP.SELF],
        "script-src": [CSP.SELF],
        "style-src": [CSP.SELF],
        "report-uri": "/csp-report/",
    },
)
@modify_settings(
    MIDDLEWARE={"append": "django.middleware.csp.ContentSecurityPolicyMiddleware"}
)
class CSPSeleniumTestCase(SeleniumTestCase, StaticLiveServerTestCase):
    available_apps = ["middleware"]

    def setUp(self):
        self.addCleanup(csp_reports.clear)
        super().setUp()

    def test_reports_are_generated(self):
        url = self.live_server_url + "/csp-failure/"
        self.selenium.get(url)
        time.sleep(1)  # Allow time for the CSP report to be sent.
        reports = sorted(
            (r["csp-report"]["document-uri"], r["csp-report"]["violated-directive"])
            for r in csp_reports
        )
        self.assertEqual(reports, [(url, "img-src"), (url, "style-src-elem")])
