from unittest import mock

from django.core.mail import EmailProviderDoesNotExist, InvalidEmailProvider, providers
from django.core.mail.backends import locmem, smtp
from django.test import SimpleTestCase, override_settings

from .tests import spy_on

dummy_provider = {"BACKEND": "django.core.mail.backends.dummy.EmailBackend"}


class EmailProvidersTests(SimpleTestCase):
    @override_settings(
        EMAIL_PROVIDERS={"default": dummy_provider, "custom": dummy_provider}
    )
    def test_getitem(self):
        with self.subTest("defined providers"):
            self.assertEqual(providers["default"].alias, "default")
            self.assertEqual(providers["custom"].alias, "custom")

        with self.subTest("providers[None] returns default provider"):
            self.assertEqual(providers[None].alias, "default")

        with self.subTest("missing provider"):
            msg = "The email provider 'unknown' is not configured."
            with self.assertRaisesMessage(EmailProviderDoesNotExist, msg):
                _ = providers["unknown"]

    @override_settings(
        EMAIL_PROVIDERS={
            "one": dummy_provider,
            "two": dummy_provider,
            "three": dummy_provider,
        }
    )
    @mock.patch("django.core.mail.backends.dummy.EmailBackend.__init__")
    def test_contains(self, mock_init):
        self.assertIn("two", providers)
        self.assertNotIn("zero", providers)
        self.assertNotIn(None, providers)
        # __contains__() does not construct any backend instance.
        mock_init.assert_not_called()

    @override_settings(
        EMAIL_PROVIDERS={
            "one": dummy_provider,
            "two": dummy_provider,
            "three": dummy_provider,
        }
    )
    @mock.patch("django.core.mail.backends.dummy.EmailBackend.__init__")
    def test_iter(self, mock_init):
        self.assertEqual(list(providers), ["one", "two", "three"])
        # __iter__() does not construct any backend instance.
        mock_init.assert_not_called()

    @override_settings(
        EMAIL_PROVIDERS={"default": dummy_provider, "custom": dummy_provider}
    )
    def test_get(self):
        with self.subTest("defined providers"):
            self.assertEqual(providers.get("default").alias, "default")
            self.assertEqual(providers.get("custom").alias, "custom")

        with self.subTest("missing provider"):
            with self.subTest("no default arg"):
                self.assertIsNone(providers.get("unknown"))
            with self.subTest("positional default arg"):
                self.assertEqual(providers.get("unknown", "foo"), "foo")
            with self.subTest("keyword default arg"):
                self.assertEqual(providers.get("unknown", default="foo"), "foo")

        with self.subTest("get(None) returns default provider"):
            self.assertEqual(providers.get(None).alias, "default")
        with self.subTest("get() returns default provider"):
            self.assertEqual(providers.get().alias, "default")

    @override_settings(EMAIL_PROVIDERS={"default": dummy_provider})
    def test_default_provider_property(self):
        backend = providers.default
        self.assertEqual(backend.alias, "default")

    # RemovedInDjango70Warning: remove override_settings (but keep the test).
    # (EMAIL_PROVIDERS={} becomes the default in Django 7.0.)
    @override_settings(EMAIL_PROVIDERS={})
    def test_default_email_providers(self):
        """No email providers are configured by default."""
        msg = "The email provider 'default' is not configured."
        with (
            self.subTest('providers["default"]'),
            self.assertRaisesMessage(EmailProviderDoesNotExist, msg),
        ):
            _ = providers["default"]
        with (
            self.subTest("providers.default"),
            self.assertRaisesMessage(EmailProviderDoesNotExist, msg),
        ):
            _ = providers.default

        with self.subTest("providers.get()"):
            self.assertIsNone(providers.get())
        with self.subTest("providers.__contains__()"):
            self.assertIs("default" in providers, False)
        with self.subTest("providers.__iter__()"):
            self.assertEqual(list(providers), [])

    @override_settings(EMAIL_PROVIDERS={"custom": dummy_provider})
    def test_default_provider_not_required(self):
        """
        Although a default provider is recommended, failing to configure one is
        not an error and does not prevent using other providers.
        """
        self.assertEqual(providers["custom"].alias, "custom")
        msg = "The email provider 'default' is not configured."
        with self.assertRaisesMessage(EmailProviderDoesNotExist, msg):
            _ = providers.default

    @override_settings(EMAIL_PROVIDERS={"custom": dummy_provider})
    def test_instances_not_cached(self):
        self.assertIsNot(providers["custom"], providers["custom"])

    @override_settings(EMAIL_PROVIDERS={"custom": {"OPTIONS": {"host": "localhost"}}})
    def test_default_backend_is_smtp(self):
        """Omitting "BACKEND" gives the SMTP EmailBackend."""
        backend = providers["custom"]
        self.assertIsInstance(backend, smtp.EmailBackend)

    @override_settings(
        EMAIL_PROVIDERS={"default": {"BACKEND": "mail.custombackend.EmailBackend"}}
    )
    def test_custom_backend(self):
        backend = providers.default
        self.assertTrue(hasattr(backend, "test_outbox"))

    @override_settings(EMAIL_PROVIDERS={"custom": {"BACKEND": "foo.bar"}})
    def test_invalid_backend(self):
        msg = (
            "EMAIL_PROVIDERS['custom']: Could not find BACKEND 'foo.bar': No "
            "module named 'foo'"
        )
        with self.assertRaisesMessage(InvalidEmailProvider, msg):
            _ = providers["custom"]

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.dummy.EmailBackend",
                "OPTIONS": {"one": 1, "false": False, "foo": "bar"},
            }
        }
    )
    @mock.patch(
        "django.core.mail.backends.dummy.EmailBackend.__init__", return_value=None
    )
    def test_options_are_provided_to_backend_init(self, mock_init):
        _ = providers["custom"]
        mock_init.assert_called_once_with(alias="custom", one=1, false=False, foo="bar")

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "OPTIONS": {"alias": "imposter", "host": "localhost"},
            }
        }
    )
    def test_alias_is_invalid_option(self):
        msg = "EMAIL_PROVIDERS['custom']: 'alias' is not allowed in OPTIONS."
        with self.assertRaisesMessage(InvalidEmailProvider, msg):
            _ = providers["custom"]
        with self.assertRaises(EmailProviderDoesNotExist):
            _ = providers["imposter"]

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.dummy.EmailBackend",
                "OPTIONS": {"unknown": "foo"},
            }
        }
    )
    def test_unknown_options(self):
        # This error message actually comes from BaseEmailBackend.
        msg = "Unknown OPTIONS for EMAIL_PROVIDERS['custom']: 'unknown'."
        with self.assertRaisesMessage(InvalidEmailProvider, msg):
            _ = providers["custom"]

    def test_does_not_exist_is_key_error(self):
        """The error from providers['unknown'] should be a KeyError"""
        self.assertTrue(issubclass(EmailProviderDoesNotExist, KeyError))

    def test_does_not_exist_is_limited_purpose(self):
        """
        Code that wants to send email only when it has been configured will
        trap and ignore EmailProviderDoesNotExist. If that error is used to
        report anything other than a missing alias key in EMAIL_PROVIDERS,
        unrelated configuration errors may be incorrectly silenced. The error's
        constructor is designed to discourage other uses.
        """
        msg = "EmailProviderDoesNotExist.__init__() takes 1 positional argument"
        with self.assertRaisesMessage(TypeError, msg):
            EmailProviderDoesNotExist("Some other configuration problem")


# RemovedInDjango70Warning.
class EmailProvidersCompatibilityTests(SimpleTestCase):
    """providers.default is usable even when EMAIL_PROVIDERS is not defined."""

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="mail.example.com",
    )
    def test_default_provider_with_deprecated_settings(self):
        backend = providers.default
        self.assertIsNone(backend.alias)
        self.assertIsInstance(backend, smtp.EmailBackend)
        self.assertEqual(backend.host, "mail.example.com")

    @spy_on(locmem.EmailBackend)
    def test_default_provider_with_no_settings(self, mock_init):
        # Django's test runner changes the default EMAIL_BACKEND to locmem.
        backend = providers.default
        # In compatibility mode, backends are constructed with no 'alias' arg.
        self.assertNotIn("alias", mock_init.call_args.kwargs)
        self.assertIsInstance(backend, locmem.EmailBackend)
        self.assertIsNone(backend.alias)

    def test_unknown_provider_with_no_settings(self):
        # Compatibility only applies to the default provider.
        msg = "The email provider 'unknown' is not configured."
        with self.assertRaisesMessage(EmailProviderDoesNotExist, msg):
            _ = providers["unknown"]
