from django.core.checks import Error, Warning, registry
from django.core.checks.mail import (
    check_mailers_default_alias,
    check_mailers_production_backend,
)
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


class MailersProductionBackendTests(SimpleTestCase):
    def test_is_deployment_only(self):
        self.assertIn(
            check_mailers_production_backend, registry.registry.deployment_checks
        )
        self.assertNotIn(
            check_mailers_production_backend, registry.registry.registered_checks
        )

    def test_mailers_not_defined(self):
        self.assertEqual(check_mailers_production_backend(None), [])

    def test_production_backends(self):
        production_backends = [
            "django.core.mail.backends.smtp.EmailBackend",
            "any.third.party.EmailBackend",
        ]
        for backend in production_backends:
            with (
                self.subTest(backend=backend),
                self.settings(MAILERS={"default": {"BACKEND": backend}}),
            ):
                self.assertEqual(check_mailers_production_backend(None), [])

    def test_non_production_backends(self):
        hint = (
            "Use a production-ready email backend, such as the SMTP backend, "
            "otherwise email will not be sent."
        )
        for backend_type in ["console", "dummy", "filebased", "locmem"]:
            backend = f"django.core.mail.backends.{backend_type}.EmailBackend"
            msg = (
                f"Your MAILERS setting uses a development-only email backend in "
                f"the 'default' entry ({backend})."
            )
            with (
                self.subTest(backend=backend),
                self.settings(MAILERS={"default": {"BACKEND": backend}}),
            ):
                self.assertEqual(
                    check_mailers_production_backend(None),
                    [Error(msg, hint=hint, id="mail.E001")],
                )

    @override_settings(
        MAILERS={
            "default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"},
            "secondary": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
        }
    )
    def test_only_applies_to_default_mailer(self):
        self.assertEqual(
            check_mailers_production_backend(None),
            [],
        )
