from django.core.mail import InvalidMailer, MailerDoesNotExist, mailers
from django.core.mail.backends import locmem, smtp
from django.test import SimpleTestCase, override_settings

from . import (
    ignore_no_default_mailer_warning,
    override_deprecated_email_settings,
)
from .custombackend import OptionsCapturingBackend


class MailersTests(SimpleTestCase):
    def setUp(self):
        self.addCleanup(OptionsCapturingBackend.reset)

    @override_settings(
        MAILERS={
            "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
            "custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
        }
    )
    def test_getitem(self):
        with self.subTest("defined mailers"):
            self.assertEqual(mailers["default"].alias, "default")
            self.assertEqual(mailers["custom"].alias, "custom")

        with self.subTest("missing mailer"):
            msg = "The mailer 'unknown' is not configured."
            with self.assertRaisesMessage(MailerDoesNotExist, msg):
                _ = mailers["unknown"]

        with self.subTest("raises KeyError"):
            # mail.mailers is a mapping, so unknown keys raise KeyError.
            # (MailerDoesNotExist must be a KeyError.)
            with self.assertRaises(KeyError):
                _ = mailers["unknown"]

    @override_settings(
        MAILERS={
            "one": {"BACKEND": "mail.custombackend.OptionsCapturingBackend"},
            "two": {"BACKEND": "mail.custombackend.OptionsCapturingBackend"},
            "three": {"BACKEND": "mail.custombackend.OptionsCapturingBackend"},
        }
    )
    def test_contains(self):
        self.assertIn("two", mailers)
        self.assertNotIn("zero", mailers)
        self.assertNotIn(None, mailers)
        # __contains__() does not construct any backend instance.
        self.assertEqual(OptionsCapturingBackend.init_kwargs, [])

    @override_settings(
        MAILERS={
            "one": {"BACKEND": "mail.custombackend.OptionsCapturingBackend"},
            "two": {"BACKEND": "mail.custombackend.OptionsCapturingBackend"},
            "three": {"BACKEND": "mail.custombackend.OptionsCapturingBackend"},
        }
    )
    def test_iter(self):
        self.assertEqual(list(mailers), ["one", "two", "three"])
        # __iter__() does not construct any backend instance.
        self.assertEqual(OptionsCapturingBackend.init_kwargs, [])

    @override_settings(
        MAILERS={
            "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
            "custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
        }
    )
    def test_get(self):
        with self.subTest("defined mailers"):
            self.assertEqual(mailers.get("default").alias, "default")
            self.assertEqual(mailers.get("custom").alias, "custom")

        with self.subTest("missing mailer"):
            with self.subTest("no default arg"):
                self.assertIsNone(mailers.get("unknown"))
            with self.subTest("positional default arg"):
                self.assertEqual(mailers.get("unknown", "foo"), "foo")
            with self.subTest("keyword default arg"):
                self.assertEqual(mailers.get("unknown", default="foo"), "foo")

    @override_settings(
        MAILERS={
            "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
        }
    )
    def test_default_mailer_property(self):
        backend = mailers.default
        self.assertEqual(backend.alias, "default")

    # RemovedInDjango70Warning: remove override_settings (but keep the test).
    # (MAILERS={} becomes the default in Django 7.0.)
    @override_settings(MAILERS={})
    def test_default_mailers(self):
        msg = "The mailer 'default' is not configured."
        with (
            self.subTest('mailers["default"]'),
            self.assertRaisesMessage(MailerDoesNotExist, msg),
        ):
            _ = mailers["default"]
        with (
            self.subTest("mailers.default"),
            self.assertRaisesMessage(MailerDoesNotExist, msg),
        ):
            _ = mailers.default

        with self.subTest("mailers.get()"):
            self.assertIsNone(mailers.get("default"))
        with self.subTest("mailers.__contains__()"):
            self.assertIs("default" in mailers, False)
        with self.subTest("mailers.__iter__()"):
            self.assertEqual(list(mailers), [])

    @override_settings(
        MAILERS={"custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    )
    def test_default_mailer_not_required(self):
        self.assertEqual(mailers["custom"].alias, "custom")
        msg = "The mailer 'default' is not configured."
        with self.assertRaisesMessage(MailerDoesNotExist, msg):
            _ = mailers.default

    @override_settings(
        MAILERS={"custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    )
    def test_instances_not_cached(self):
        self.assertIsNot(mailers["custom"], mailers["custom"])

    @override_settings(MAILERS={"custom": {"OPTIONS": {"host": "localhost"}}})
    def test_default_backend_is_smtp(self):
        # Omitting "BACKEND" gives the SMTP EmailBackend.
        backend = mailers["custom"]
        self.assertIsInstance(backend, smtp.EmailBackend)

    @override_settings(
        MAILERS={"default": {"BACKEND": "mail.custombackend.EmailBackend"}}
    )
    def test_custom_backend(self):
        backend = mailers.default
        self.assertTrue(hasattr(backend, "test_outbox"))

    @override_settings(MAILERS={"custom": {"BACKEND": "foo.bar"}})
    def test_invalid_backend(self):
        msg = (
            "MAILERS['custom']: Could not find BACKEND 'foo.bar': No "
            "module named 'foo'"
        )
        with self.assertRaisesMessage(InvalidMailer, msg):
            _ = mailers["custom"]

    @override_settings(
        MAILERS={
            "custom": {
                "BACKEND": "mail.custombackend.OptionsCapturingBackend",
                "OPTIONS": {"one": 1, "false": False, "foo": "bar"},
            }
        }
    )
    def test_options_are_provided_to_backend_init(self):
        _ = mailers["custom"]
        self.assertEqual(
            OptionsCapturingBackend.init_kwargs[0],
            {"alias": "custom", "one": 1, "false": False, "foo": "bar"},
        )

    @override_settings(
        MAILERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "OPTIONS": {"alias": "imposter", "host": "localhost"},
            }
        }
    )
    def test_alias_is_invalid_option(self):
        msg = "MAILERS['custom']: OPTIONS must not define 'alias'."
        with self.assertRaisesMessage(InvalidMailer, msg):
            _ = mailers["custom"]
        with self.assertRaises(MailerDoesNotExist):
            _ = mailers["imposter"]

    @override_settings(
        MAILERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
                "OPTIONS": {"unknown": "foo"},
            }
        }
    )
    def test_unknown_options(self):
        # This error message actually comes from BaseEmailBackend.
        msg = "MAILERS['custom']: Unknown options 'unknown'."
        with self.assertRaisesMessage(InvalidMailer, msg):
            _ = mailers["custom"]

    def test_does_not_exist_is_limited_purpose(self):
        # Code that wants to send email only when it has been configured will
        # trap and ignore MailerDoesNotExist. If that error is used to
        # report anything other than a missing alias key in MAILERS,
        # unrelated configuration errors may be incorrectly silenced. The
        # error's constructor is designed to discourage other uses.
        msg = "MailerDoesNotExist.__init__() takes 1 positional argument"
        with self.assertRaisesMessage(TypeError, msg):
            MailerDoesNotExist("Some other configuration problem")


# RemovedInDjango70Warning.
class MailersCompatibilityTests(SimpleTestCase):
    """mailers.default is usable even when MAILERS is not defined."""

    @override_deprecated_email_settings(
        EMAIL_BACKEND="mail.custombackend.OptionsCapturingBackend"
    )
    def test_default_mailer_with_deprecated_settings(self):
        self.addCleanup(OptionsCapturingBackend.reset)
        backend = mailers.default
        self.assertIsNone(backend.alias)
        self.assertIsInstance(backend, OptionsCapturingBackend)
        self.assertNotIn("alias", OptionsCapturingBackend.init_kwargs[0])

    @ignore_no_default_mailer_warning()
    def test_default_mailer_with_no_settings(self):
        backend = mailers.default
        # Django's test runner changes the default EMAIL_BACKEND to locmem.
        self.assertIsInstance(backend, locmem.EmailBackend)
        # In compatibility mode, backends are constructed with no 'alias' arg.
        self.assertIsNone(backend.alias)

    def test_unknown_mailer_with_no_settings(self):
        # Compatibility only applies to the default mailer.
        msg = "The mailer 'unknown' is not configured."
        with self.assertRaisesMessage(MailerDoesNotExist, msg):
            _ = mailers["unknown"]
