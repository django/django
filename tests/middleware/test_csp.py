from django.http import HttpRequest, HttpResponse
from django.middleware.constants import CSP
from django.middleware.csp import ContentSecurityPolicyMiddleware, LazyNonce
from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils.functional import empty

HEADER = "Content-Security-Policy"
HEADER_REPORT_ONLY = "Content-Security-Policy-Report-Only"

basic_config = {
    "default-src": [CSP.SELF],
}
alt_config = {
    "default-src": [CSP.SELF, CSP.UNSAFE_INLINE],
}
basic_policy = "default-src 'self'"


class CSPBuildPolicyTest(SimpleTestCase):
    def build_policy(self, policy, nonce=None):
        return ContentSecurityPolicyMiddleware.build_policy(policy, nonce)

    def assertPolicyEqual(self, a, b):
        parts_a = sorted(a.split("; ")) if a is not None else None
        parts_b = sorted(b.split("; ")) if b is not None else None
        self.assertEqual(parts_a, parts_b, f"Policies not equal: {a!r} != {b!r}")

    def test_config_empty(self):
        self.assertPolicyEqual(self.build_policy({}), "")

    def test_config_basic(self):
        self.assertPolicyEqual(self.build_policy(basic_config), basic_policy)

    def test_config_multiple_directives(self):
        policy = {
            "default-src": [CSP.SELF],
            "script-src": [CSP.NONE],
        }
        self.assertPolicyEqual(
            self.build_policy(policy), "default-src 'self'; script-src 'none'"
        )

    def test_config_value_as_string(self):
        """
        Test that a single value can be passed as a string.
        """
        policy = {"default-src": CSP.SELF}
        self.assertPolicyEqual(self.build_policy(policy), "default-src 'self'")

    def test_config_value_as_tuple(self):
        """
        Test that a tuple can be passed as a value.
        """
        policy = {"default-src": (CSP.SELF, "foo.com")}
        self.assertPolicyEqual(self.build_policy(policy), "default-src 'self' foo.com")

    def test_config_value_as_set(self):
        """
        Test that a set can be passed as a value.

        Sets are often used in Django settings to ensure uniqueness, however, sets are
        unordered. The middleware ensures consistency via sorting if a set is passed.
        """
        policy = {"default-src": {CSP.SELF, "foo.com", "bar.com"}}
        self.assertPolicyEqual(
            self.build_policy(policy), "default-src 'self' bar.com foo.com"
        )

    def test_config_value_none(self):
        """
        Test that `None` removes the directive from the policy.

        Useful in cases where the CSP config is scripted in some way or
        explicitly not wanting to set a directive.
        """
        policy = {"default-src": [CSP.SELF], "script-src": None}
        self.assertPolicyEqual(self.build_policy(policy), basic_policy)

    def test_config_value_boolean_true(self):
        policy = {"default-src": [CSP.SELF], "block-all-mixed-content": True}
        self.assertPolicyEqual(
            self.build_policy(policy), "default-src 'self'; block-all-mixed-content"
        )

    def test_config_value_boolean_false(self):
        policy = {"default-src": [CSP.SELF], "block-all-mixed-content": False}
        self.assertPolicyEqual(self.build_policy(policy), basic_policy)

    def test_config_value_multiple_boolean(self):
        policy = {
            "default-src": [CSP.SELF],
            "block-all-mixed-content": True,
            "upgrade-insecure-requests": True,
        }
        self.assertPolicyEqual(
            self.build_policy(policy),
            "default-src 'self'; block-all-mixed-content; upgrade-insecure-requests",
        )

    def test_config_with_nonce_arg(self):
        """
        Test when the `CSP.NONCE` is not in the defined policy, the nonce
        argument has no effect.
        """
        self.assertPolicyEqual(
            self.build_policy(basic_config, nonce="abc123"), basic_policy
        )

    def test_config_with_nonce(self):
        policy = {"default-src": [CSP.SELF, CSP.NONCE]}
        self.assertPolicyEqual(
            self.build_policy(policy, nonce="abc123"),
            "default-src 'self' 'nonce-abc123'",
        )

    def test_config_with_multiple_nonces(self):
        policy = {
            "default-src": [CSP.SELF, CSP.NONCE],
            "script-src": [CSP.SELF, CSP.NONCE],
        }
        self.assertPolicyEqual(
            self.build_policy(policy, nonce="abc123"),
            "default-src 'self' 'nonce-abc123'; script-src 'self' 'nonce-abc123'",
        )

    def test_config_with_empty_directive(self):
        policy = {"default-src": []}
        self.assertPolicyEqual(self.build_policy(policy), "")


class CSPGetPolicyTest(SimpleTestCase):
    def get_policy(self, request, response, report_only=False):
        return ContentSecurityPolicyMiddleware.get_policy(
            request, response, report_only
        )

    def test_default(self):
        request = HttpRequest()
        response = HttpResponse()
        nonce = LazyNonce()
        request.csp_nonce = nonce
        self.assertEqual(self.get_policy(request, response), (None, None))
        str(nonce)  # Force the nonce to be generated.
        self.assertEqual(self.get_policy(request, response), (None, nonce))

    def test_default_report_only(self):
        request = HttpRequest()
        response = HttpResponse()
        nonce = LazyNonce()
        request.csp_nonce = nonce
        self.assertEqual(
            self.get_policy(request, response, report_only=True), (None, None)
        )
        str(nonce)  # Force the nonce to be generated.
        self.assertEqual(self.get_policy(request, response), (None, nonce))

    def test_settings(self):
        request = HttpRequest()
        response = HttpResponse()
        nonce = LazyNonce()
        request.csp_nonce = nonce
        with self.settings(SECURE_CSP=basic_config):
            self.assertEqual(self.get_policy(request, response), (basic_config, None))
            str(nonce)  # Force the nonce to be generated.
            self.assertEqual(self.get_policy(request, response), (basic_config, nonce))

    def test_settings_report_only(self):
        request = HttpRequest()
        response = HttpResponse()
        nonce = LazyNonce()
        request.csp_nonce = nonce
        with self.settings(SECURE_CSP_REPORT_ONLY=basic_config):
            self.assertEqual(
                self.get_policy(request, response, report_only=True),
                (basic_config, None),
            )
            str(nonce)  # Force the nonce to be generated.
            self.assertEqual(
                self.get_policy(request, response, report_only=True),
                (basic_config, nonce),
            )

    def test_response_override(self):
        request = HttpRequest()
        response = HttpResponse()
        response._csp_config = basic_config
        nonce = LazyNonce()
        request.csp_nonce = nonce
        with self.settings(SECURE_CSP=alt_config):
            self.assertEqual(self.get_policy(request, response), (basic_config, None))
            str(nonce)  # Force the nonce to be generated.
            self.assertEqual(self.get_policy(request, response), (basic_config, nonce))

    def test_response_override_report_only(self):
        request = HttpRequest()
        response = HttpResponse()
        response._csp_config_ro = basic_config
        nonce = LazyNonce()
        request.csp_nonce = nonce
        with self.settings(SECURE_CSP=alt_config):
            self.assertEqual(
                self.get_policy(request, response, report_only=True),
                (basic_config, None),
            )
            str(nonce)  # Force the nonce to be generated.
            self.assertEqual(
                self.get_policy(request, response, report_only=True),
                (basic_config, nonce),
            )


@override_settings(
    MIDDLEWARE=["django.middleware.csp.ContentSecurityPolicyMiddleware"],
    ROOT_URLCONF="middleware.urls",
)
class CSPMiddlewareTest(SimpleTestCase):
    def test_constants(self):
        self.assertEqual(HEADER, "Content-Security-Policy")
        self.assertEqual(HEADER_REPORT_ONLY, "Content-Security-Policy-Report-Only")

    def test_csp_defaults_off(self):
        response = self.client.get("/csp-base/")
        self.assertNotIn(HEADER, response)
        self.assertNotIn(HEADER_REPORT_ONLY, response)

    @override_settings(SECURE_CSP=basic_config)
    def test_csp_basic(self):
        """
        With SECURE_CSP set to a valid value, the middleware adds a
        "Content-Security-Policy" header to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[HEADER], basic_policy)
        self.assertNotIn(HEADER_REPORT_ONLY, response)

    @override_settings(SECURE_CSP={"default-src": [CSP.SELF, CSP.NONCE]})
    def test_csp_basic_with_nonce(self):
        """
        Test the nonce is added to the header and matches what is in the view.
        """
        response = self.client.get("/csp-nonce/")
        nonce = response.content.decode()
        self.assertTrue(nonce)
        self.assertEqual(response[HEADER], f"default-src 'self' 'nonce-{nonce}'")

    @override_settings(SECURE_CSP={"default-src": [CSP.SELF, CSP.NONCE]})
    def test_csp_basic_with_nonce_but_unused(self):
        """
        Test if `request.csp_nonce` is never accessed, it is not added to the header.
        """
        response = self.client.get("/csp-base/")
        nonce = response.content.decode()
        self.assertIsNotNone(nonce)
        self.assertEqual(response[HEADER], basic_policy)

    @override_settings(SECURE_CSP_REPORT_ONLY=basic_config)
    def test_csp_report_only_basic(self):
        """
        With SECURE_CSP_REPORT_ONLY set to a valid value, the middleware adds a
        "Content-Security-Policy-Report-Only" header to the response.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[HEADER_REPORT_ONLY], basic_policy)
        self.assertNotIn(HEADER, response)

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
        self.assertEqual(response[HEADER], basic_policy)
        self.assertEqual(response[HEADER_REPORT_ONLY], basic_policy)

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
        self.assertNotIn(HEADER, response)
        self.assertNotIn(HEADER_REPORT_ONLY, response)

    @override_settings(
        DEBUG=True,
        SECURE_CSP=basic_config,
        SECURE_CSP_REPORT_ONLY=basic_config,
    )
    def test_csp_500_debug_view(self):
        """
        Test that the CSP headers are not added to the debug view.
        """
        response = self.client.get("/csp-500/")
        self.assertNotIn(HEADER, response)
        self.assertNotIn(HEADER_REPORT_ONLY, response)


@override_settings(
    MIDDLEWARE=["django.middleware.csp.ContentSecurityPolicyMiddleware"],
    ROOT_URLCONF="middleware.urls",
    SECURE_CSP=basic_config,
    SECURE_CSP_REPORT_ONLY=basic_config,
)
class CSPMiddlewareWithDecoratedViewsTest(SimpleTestCase):
    def test_no_decorators(self):
        """
        Test the base state.
        """
        response = self.client.get("/csp-base/")
        self.assertEqual(response[HEADER], basic_policy)
        self.assertEqual(response[HEADER_REPORT_ONLY], basic_policy)

    def test_csp_disabled_both(self):
        """
        Test that `csp_disabled` will clear both headers.
        """
        response = self.client.get("/csp-disabled/")
        self.assertNotIn(HEADER, response)
        self.assertNotIn(HEADER_REPORT_ONLY, response)

    def test_csp_disabled_decorator(self):
        """
        Test that `csp_disabled` will clear the enforced header.
        """
        response = self.client.get("/csp-disabled-enforced/")
        self.assertNotIn(HEADER, response)
        self.assertEqual(response[HEADER_REPORT_ONLY], basic_policy)

    def test_csp_disabled_report_only_decorator(self):
        """
        Test that `csp_disabled` will clear the report-only header.
        """
        response = self.client.get("/csp-disabled-report-only/")
        self.assertNotIn(HEADER_REPORT_ONLY, response)
        self.assertEqual(response[HEADER], basic_policy)

    def test_csp_override_enforced_decorator(self):
        """
        Test the `csp_override` decorator overrides the CSP enforced Django settings.
        """
        response = self.client.get("/override-csp-enforced/")
        self.assertEqual(response[HEADER], "default-src 'self'; img-src 'self' data:")
        self.assertEqual(response[HEADER_REPORT_ONLY], basic_policy)

    def test_csp_override_report_only_decorator(self):
        """
        Test the `csp_override` decorator overrides the CSP report-only Django settings.
        """
        response = self.client.get("/override-csp-report-only/")
        self.assertEqual(
            response[HEADER_REPORT_ONLY], "default-src 'self'; img-src 'self' data:"
        )
        self.assertEqual(response[HEADER], basic_policy)

    def test_csp_override_both_decorator(self):
        """
        Test the `csp_override` decorator overrides both CSP Django settings.
        """
        response = self.client.get("/override-csp-both/")
        self.assertEqual(response[HEADER], "default-src 'self'; img-src 'self' data:")
        self.assertEqual(
            response[HEADER_REPORT_ONLY], "default-src 'self'; img-src 'self' data:"
        )


class LazyNonceTests(SimpleTestCase):
    def test_generates_on_usage(self):
        nonce = LazyNonce()
        self.assertFalse(nonce)
        self.assertIs(nonce._wrapped, empty)

        # Force usage, similar to template rendering, to generate the nonce.
        val = str(nonce)

        self.assertTrue(nonce)
        self.assertEqual(nonce, val)
        self.assertIsInstance(nonce, str)
        self.assertEqual(len(val), 22)  # Based on secrets.token_urlsafe of 16 bytes.

        # Also test the wrapped value.
        self.assertEqual(nonce._wrapped, val)

    def test_returns_same_value(self):
        nonce = LazyNonce()
        first = str(nonce)
        second = str(nonce)

        self.assertEqual(first, second)
