from secrets import token_urlsafe
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils.csp import CSP, LazyNonce, build_policy
from django.utils.functional import empty

basic_config = {
    "default-src": [CSP.SELF],
}
alt_config = {
    "default-src": [CSP.SELF, CSP.UNSAFE_INLINE],
}
basic_policy = "default-src 'self'"


class CSPConstantsTests(SimpleTestCase):
    def test_constants(self):
        self.assertEqual(CSP.NONE, "'none'")
        self.assertEqual(CSP.REPORT_SAMPLE, "'report-sample'")
        self.assertEqual(CSP.SELF, "'self'")
        self.assertEqual(CSP.STRICT_DYNAMIC, "'strict-dynamic'")
        self.assertEqual(CSP.UNSAFE_EVAL, "'unsafe-eval'")
        self.assertEqual(CSP.UNSAFE_HASHES, "'unsafe-hashes'")
        self.assertEqual(CSP.UNSAFE_INLINE, "'unsafe-inline'")
        self.assertEqual(CSP.WASM_UNSAFE_EVAL, "'wasm-unsafe-eval'")
        self.assertEqual(CSP.NONCE, "<CSP_NONCE_SENTINEL>")


class CSPBuildPolicyTest(SimpleTestCase):

    def assertPolicyEqual(self, a, b):
        parts_a = sorted(a.split("; ")) if a is not None else None
        parts_b = sorted(b.split("; ")) if b is not None else None
        self.assertEqual(parts_a, parts_b, f"Policies not equal: {a!r} != {b!r}")

    def test_config_empty(self):
        self.assertPolicyEqual(build_policy({}), "")

    def test_config_basic(self):
        self.assertPolicyEqual(build_policy(basic_config), basic_policy)

    def test_config_multiple_directives(self):
        policy = {
            "default-src": [CSP.SELF],
            "script-src": [CSP.NONE],
        }
        self.assertPolicyEqual(
            build_policy(policy), "default-src 'self'; script-src 'none'"
        )

    def test_config_value_as_string(self):
        """
        Test that a single value can be passed as a string.
        """
        policy = {"default-src": CSP.SELF}
        self.assertPolicyEqual(build_policy(policy), "default-src 'self'")

    def test_config_value_as_tuple(self):
        """
        Test that a tuple can be passed as a value.
        """
        policy = {"default-src": (CSP.SELF, "foo.com")}
        self.assertPolicyEqual(build_policy(policy), "default-src 'self' foo.com")

    def test_config_value_as_set(self):
        """
        Test that a set can be passed as a value.

        Sets are often used in Django settings to ensure uniqueness, however,
        sets are unordered. The middleware ensures consistency via sorting if a
        set is passed.
        """
        policy = {"default-src": {CSP.SELF, "foo.com", "bar.com"}}
        self.assertPolicyEqual(
            build_policy(policy), "default-src 'self' bar.com foo.com"
        )

    def test_config_value_none(self):
        """
        Test that `None` removes the directive from the policy.

        Useful in cases where the CSP config is scripted in some way or
        explicitly not wanting to set a directive.
        """
        policy = {"default-src": [CSP.SELF], "script-src": None}
        self.assertPolicyEqual(build_policy(policy), basic_policy)

    def test_config_value_boolean_true(self):
        policy = {"default-src": [CSP.SELF], "block-all-mixed-content": True}
        self.assertPolicyEqual(
            build_policy(policy), "default-src 'self'; block-all-mixed-content"
        )

    def test_config_value_boolean_false(self):
        policy = {"default-src": [CSP.SELF], "block-all-mixed-content": False}
        self.assertPolicyEqual(build_policy(policy), basic_policy)

    def test_config_value_multiple_boolean(self):
        policy = {
            "default-src": [CSP.SELF],
            "block-all-mixed-content": True,
            "upgrade-insecure-requests": True,
        }
        self.assertPolicyEqual(
            build_policy(policy),
            "default-src 'self'; block-all-mixed-content; upgrade-insecure-requests",
        )

    def test_config_with_nonce_arg(self):
        """
        Test when the `CSP.NONCE` is not in the defined policy, the nonce
        argument has no effect.
        """
        self.assertPolicyEqual(build_policy(basic_config, nonce="abc123"), basic_policy)

    def test_config_with_nonce(self):
        policy = {"default-src": [CSP.SELF, CSP.NONCE]}
        self.assertPolicyEqual(
            build_policy(policy, nonce="abc123"),
            "default-src 'self' 'nonce-abc123'",
        )

    def test_config_with_multiple_nonces(self):
        policy = {
            "default-src": [CSP.SELF, CSP.NONCE],
            "script-src": [CSP.SELF, CSP.NONCE],
        }
        self.assertPolicyEqual(
            build_policy(policy, nonce="abc123"),
            "default-src 'self' 'nonce-abc123'; script-src 'self' 'nonce-abc123'",
        )

    def test_config_with_empty_directive(self):
        policy = {"default-src": []}
        self.assertPolicyEqual(build_policy(policy), "")


class LazyNonceTests(SimpleTestCase):
    def test_generates_on_usage(self):
        generated_tokens = []
        nonce = LazyNonce()
        self.assertFalse(nonce)
        self.assertIs(nonce._wrapped, empty)

        def memento_token_urlsafe(size):
            generated_tokens.append(result := token_urlsafe(size))
            return result

        with patch("django.utils.csp.secrets.token_urlsafe", memento_token_urlsafe):
            # Force usage, similar to template rendering, to generate the
            # nonce.
            val = str(nonce)

        self.assertTrue(nonce)
        self.assertEqual(nonce, val)
        self.assertIsInstance(nonce, str)
        self.assertEqual(len(val), 22)  # Based on secrets.token_urlsafe of 16 bytes.
        self.assertEqual(generated_tokens, [nonce])
        # Also test the wrapped value.
        self.assertEqual(nonce._wrapped, val)

    def test_returns_same_value(self):
        nonce = LazyNonce()
        first = str(nonce)
        second = str(nonce)

        self.assertEqual(first, second)
