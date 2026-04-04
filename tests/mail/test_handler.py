from unittest import mock

from django.core.mail import EmailProviderDoesNotExist, InvalidEmailProvider, providers
from django.core.mail.backends import locmem, smtp
from django.test import SimpleTestCase, override_settings

from .custombackend import InitCheckBackend


class EmailProvidersTests(SimpleTestCase):
    def setUp(self):
        InitCheckBackend.init_kwargs = None

    @override_settings(
        EMAIL_PROVIDERS={
            "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
            "custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
        }
    )
    def test_getitem(self):
        with self.subTest("defined providers"):
            self.assertEqual(providers["default"].alias, "default")
            self.assertEqual(providers["custom"].alias, "custom")

        with self.subTest("missing provider"):
            msg = "The email provider 'unknown' is not configured."
            with self.assertRaisesMessage(EmailProviderDoesNotExist, msg) as cm:
                _ = providers["unknown"]
            # `except KeyError` would catch EmailProviderDoesNotExist.
            self.assertIsInstance(cm.exception, KeyError)

    @override_settings(
        EMAIL_PROVIDERS={
            "one": {"BACKEND": "mail.custombackend.InitCheckBackend"},
            "two": {"BACKEND": "mail.custombackend.InitCheckBackend"},
            "three": {"BACKEND": "mail.custombackend.InitCheckBackend"},
        }
    )
    def test_contains(self):
        self.assertIn("two", providers)
        self.assertNotIn("zero", providers)
        self.assertNotIn(None, providers)
        # __contains__() does not construct any backend instance.
        self.assertIsNone(InitCheckBackend.init_kwargs)

    @override_settings(
        EMAIL_PROVIDERS={
            "one": {"BACKEND": "mail.custombackend.InitCheckBackend"},
            "two": {"BACKEND": "mail.custombackend.InitCheckBackend"},
            "three": {"BACKEND": "mail.custombackend.InitCheckBackend"},
        }
    )
    def test_iter(self):
        self.assertEqual(list(providers), ["one", "two", "three"])
        # __iter__() does not construct any backend instance.
        self.assertIsNone(InitCheckBackend.init_kwargs)

    @override_settings(
        EMAIL_PROVIDERS={
            "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
            "custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
        }
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

    @override_settings(
        EMAIL_PROVIDERS={
            "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
        }
    )
    def test_default_provider_property(self):
        backend = providers.default
        self.assertEqual(backend.alias, "default")

    # RemovedInDjango70Warning: remove override_settings (but keep the test).
    # (EMAIL_PROVIDERS={} becomes the default in Django 7.0.)
    @override_settings(EMAIL_PROVIDERS={})
    def test_default_email_providers(self):
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
            self.assertIsNone(providers.get("default"))
        with self.subTest("providers.__contains__()"):
            self.assertIs("default" in providers, False)
        with self.subTest("providers.__iter__()"):
            self.assertEqual(list(providers), [])

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
        }
    )
    def test_default_provider_not_required(self):
        self.assertEqual(providers["custom"].alias, "custom")
        msg = "The email provider 'default' is not configured."
        with self.assertRaisesMessage(EmailProviderDoesNotExist, msg):
            _ = providers.default

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
        }
    )
    def test_instances_not_cached(self):
        self.assertIsNot(providers["custom"], providers["custom"])

    @override_settings(EMAIL_PROVIDERS={"custom": {"OPTIONS": {"host": "localhost"}}})
    def test_default_backend_is_smtp(self):
        # Omitting "BACKEND" gives the SMTP EmailBackend.
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
                "BACKEND": "mail.custombackend.InitCheckBackend",
                "OPTIONS": {"one": 1, "false": False, "foo": "bar"},
            }
        }
    )
    def test_options_are_provided_to_backend_init(self):
        _ = providers["custom"]
        self.assertEqual(
            InitCheckBackend.init_kwargs, {"one": 1, "false": False, "foo": "bar"}
        )

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "OPTIONS": {"alias": "imposter", "host": "localhost"},
            }
        }
    )
    def test_alias_is_invalid_option(self):
        msg = "EMAIL_PROVIDERS['custom']: OPTIONS must not define 'alias'."
        with self.assertRaisesMessage(InvalidEmailProvider, msg):
            _ = providers["custom"]
        with self.assertRaises(EmailProviderDoesNotExist):
            _ = providers["imposter"]

    @override_settings(
        EMAIL_PROVIDERS={
            "custom": {
                "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
                "OPTIONS": {"unknown": "foo"},
            }
        }
    )
    def test_unknown_options(self):
        # This error message actually comes from BaseEmailBackend.
        msg = "EMAIL_PROVIDERS['custom']: Unknown OPTIONS 'unknown'."
        with self.assertRaisesMessage(InvalidEmailProvider, msg):
            _ = providers["custom"]

    def test_does_not_exist_is_limited_purpose(self):
        # Code that wants to send email only when it has been configured will
        # trap and ignore EmailProviderDoesNotExist. If that error is used to
        # report anything other than a missing alias key in EMAIL_PROVIDERS,
        # unrelated configuration errors may be incorrectly silenced. The
        # error's constructor is designed to discourage other uses.
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

    def test_default_provider_with_no_settings(self):
        # Django's test runner changes the default EMAIL_BACKEND to locmem.
        with mock.patch.object(
            locmem.EmailBackend,
            "__init__",
            autospec=True,
            wraps=locmem.EmailBackend.__init__,
        ) as mock_init:
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
