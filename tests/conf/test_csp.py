from django.conf import csp
from django.test import SimpleTestCase


class CSPConstantsTests(SimpleTestCase):
    def test_constants(self):
        self.assertEqual(csp.HEADER, "Content-Security-Policy")
        self.assertEqual(csp.HEADER_REPORT_ONLY, "Content-Security-Policy-Report-Only")
        self.assertEqual(csp.NONE, "'none'")
        self.assertEqual(csp.REPORT_SAMPLE, "'report-sample'")
        self.assertEqual(csp.SELF, "'self'")
        self.assertEqual(csp.STRICT_DYNAMIC, "'strict-dynamic'")
        self.assertEqual(csp.UNSAFE_ALLOW_REDIRECTS, "'unsafe-allow-redirects'")
        self.assertEqual(csp.UNSAFE_EVAL, "'unsafe-eval'")
        self.assertEqual(csp.UNSAFE_HASHES, "'unsafe-hashes'")
        self.assertEqual(csp.UNSAFE_INLINE, "'unsafe-inline'")
        self.assertEqual(csp.WASM_UNSAFE_EVAL, "'wasm-unsafe-eval'")

    def test_nonce_sentinel(self):
        self.assertEqual(csp.Nonce(), csp.Nonce())
        self.assertEqual(csp.NONCE, csp.Nonce())
        self.assertEqual(repr(csp.Nonce()), "django.conf.csp.NONCE")
