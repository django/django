from django.middleware.constants import CSP
from django.test import SimpleTestCase


class CSPConstantsTests(SimpleTestCase):
    def test_constants(self):
        self.assertEqual(CSP.NONE, "'none'")
        self.assertEqual(CSP.REPORT_SAMPLE, "'report-sample'")
        self.assertEqual(CSP.SELF, "'self'")
        self.assertEqual(CSP.STRICT_DYNAMIC, "'strict-dynamic'")
        self.assertEqual(CSP.UNSAFE_ALLOW_REDIRECTS, "'unsafe-allow-redirects'")
        self.assertEqual(CSP.UNSAFE_EVAL, "'unsafe-eval'")
        self.assertEqual(CSP.UNSAFE_HASHES, "'unsafe-hashes'")
        self.assertEqual(CSP.UNSAFE_INLINE, "'unsafe-inline'")
        self.assertEqual(CSP.WASM_UNSAFE_EVAL, "'wasm-unsafe-eval'")
        self.assertEqual(CSP.NONCE, "<CSP_NONCE_SENTINEL>")
