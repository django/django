from django.core.checks import Warning
from django.core.checks.compatibility.django_7_0 import check_mailers_default_alias
from django.test import SimpleTestCase, override_settings


class MailersDefaultAliasCheckTests(SimpleTestCase):
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
                    "There is no 'default' configuration in your MAILERS setting.",
                    hint="Sending email will cause an error.",
                    id="7_0.W001",
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
                    "There is no 'default' configuration in your MAILERS setting.",
                    hint="Sending email without specifying 'using' will cause an error.",
                    id="7_0.W001",
                )
            ],
        )
