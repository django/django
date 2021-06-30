from mango.core.checks import Error
from mango.core.checks.compatibility.mango_4_0 import (
    check_csrf_trusted_origins,
)
from mango.test import SimpleTestCase
from mango.test.utils import override_settings


class CheckCSRFTrustedOrigins(SimpleTestCase):

    @override_settings(CSRF_TRUSTED_ORIGINS=['example.com'])
    def test_invalid_url(self):
        self.assertEqual(check_csrf_trusted_origins(None), [
            Error(
                'As of Mango 4.0, the values in the CSRF_TRUSTED_ORIGINS '
                'setting must start with a scheme (usually http:// or '
                'https://) but found example.com. See the release notes for '
                'details.',
                id='4_0.E001',
            )
        ])

    @override_settings(
        CSRF_TRUSTED_ORIGINS=['http://example.com', 'https://example.com'],
    )
    def test_valid_urls(self):
        self.assertEqual(check_csrf_trusted_origins(None), [])
