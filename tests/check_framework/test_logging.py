from django.core.checks import Error
from django.core.checks.logging import check_admins_managers_emails
from django.test import SimpleTestCase
from django.test.utils import override_settings


class LoggingCheckTests(SimpleTestCase):
    @override_settings(
        ADMINS=[('Admin', 'admin@example.com')],
        MANAGERS=[],
    )
    def test_valid_emails(self):
        self.assertEqual(check_admins_managers_emails(), [])

    @override_settings(
        ADMINS=[('Admin', 'admin@@example.com')],
        MANAGERS=[('Manager', 'manager@example..com')],
    )
    def test_invalid_emails(self):
        self.assertEqual(check_admins_managers_emails(), [
            Error(
                'The following email addresses in the ADMINS/MANAGERS setting are invalid:'
                ' admin@@example.com, manager@example..com',
                id='logging.E001',
            )
        ])
