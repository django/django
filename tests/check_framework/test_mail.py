from django.core.checks import Warning
from django.core.checks.mail import check_mailers_default_alias
from django.test import SimpleTestCase, override_settings


class MailersDefaultAliasCheckTests(SimpleTestCase):
    def test_mailers_not_defined(self):
        self.assertEqual(check_mailers_default_alias(None), [])

    @override_settings(
        MAILERS={
            "default": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            }
        }
    )
    def test_mailers_default_alias_configured(self):
        self.assertEqual(check_mailers_default_alias(None), [])

    @override_settings(MAILERS={})
    def test_mailers_empty(self):
        self.assertEqual(
            check_mailers_default_alias(None),
            [
                Warning(
                    "Your MAILERS setting has no 'default' entry. Sending email "
                    "without a valid mailer will fail.",
                    hint="Add a 'default' entry to MAILERS.",
                    id="mail.W001",
                )
            ],
        )

    @override_settings(
        MAILERS={
            "secondary": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            }
        }
    )
    def test_mailers_without_default_alias(self):
        self.assertEqual(
            check_mailers_default_alias(None),
            [
                Warning(
                    "Your MAILERS setting has no 'default' entry. Sending email "
                    "without a valid mailer will fail.",
                    hint=(
                        "Add a 'default' entry to MAILERS, or pass 'using' when "
                        "sending email."
                    ),
                    id="mail.W001",
                )
            ],
        )
