# RemovedInDjango70Warning: This entire file.
import types
import warnings
from email.mime.text import MIMEText
from unittest import mock

from django.conf import LazySettings, settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import (
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
)
from django.core.mail.message import forbid_multi_line_headers, sanitize_address
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango70Warning

from .tests import MailTestsMixin


class DeprecationWarningTests(MailTestsMixin, SimpleTestCase):
    def test_deprecated_on_import(self):
        """
        These items are not typically called from user code,
        so generate deprecation warnings immediately at the time
        they are imported from django.core.mail.
        """
        cases = [
            # name, msg
            (
                "BadHeaderError",
                "BadHeaderError is deprecated. Replace with ValueError.",
            ),
            (
                "SafeMIMEText",
                "SafeMIMEText is deprecated. The return value of"
                " EmailMessage.message() is an email.message.EmailMessage.",
            ),
            (
                "SafeMIMEMultipart",
                "SafeMIMEMultipart is deprecated. The return value of"
                " EmailMessage.message() is an email.message.EmailMessage.",
            ),
        ]
        for name, msg in cases:
            with self.subTest(name=name):
                with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
                    __import__("django.core.mail", fromlist=[name])

    def test_sanitize_address_deprecated(self):
        msg = (
            "The internal API sanitize_address() is deprecated."
            " Python's modern email API (with email.message.EmailMessage or"
            " email.policy.default) will handle most required validation and"
            " encoding. Use Python's email.headerregistry.Address to construct"
            " formatted addresses from component parts."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            sanitize_address("to@example.com", "ascii")

    def test_forbid_multi_line_headers_deprecated(self):
        msg = (
            "The internal API forbid_multi_line_headers() is deprecated."
            " Python's modern email API (with email.message.EmailMessage or"
            " email.policy.default) will reject multi-line headers."
        )
        with self.assertWarnsMessage(RemovedInDjango70Warning, msg):
            forbid_multi_line_headers("To", "to@example.com", "ascii")


class UndocumentedFeatureErrorTests(SimpleTestCase):
    """
    These undocumented features were removed without going through deprecation.
    In case they were being used, they now raise errors.
    """

    def test_undocumented_mixed_subtype(self):
        """
        Trying to use the previously undocumented, now unsupported
        EmailMessage.mixed_subtype causes an error.
        """
        msg = (
            "EmailMessage no longer supports"
            " the undocumented `mixed_subtype` attribute"
        )
        email = EmailMessage(
            attachments=[EmailAttachment(None, b"GIF89a...", "image/gif")]
        )
        email.mixed_subtype = "related"
        with self.assertRaisesMessage(AttributeError, msg):
            email.message()

    def test_undocumented_alternative_subtype(self):
        """
        Trying to use the previously undocumented, now unsupported
        EmailMultiAlternatives.alternative_subtype causes an error.
        """
        msg = (
            "EmailMultiAlternatives no longer supports"
            " the undocumented `alternative_subtype` attribute"
        )
        email = EmailMultiAlternatives(
            alternatives=[EmailAlternative("", "text/plain")]
        )
        email.alternative_subtype = "multilingual"
        with self.assertRaisesMessage(AttributeError, msg):
            email.message()

    def test_undocumented_get_connection_override_no_longer_supported(self):

        class CustomEmailMessage(EmailMessage):
            def get_connection(self, fail_silently=False):
                return None

        email = CustomEmailMessage(to=["to@example.com"])

        msg = (
            "EmailMessage no longer supports the undocumented "
            "get_connection() method."
        )
        with self.assertRaisesMessage(AttributeError, msg):
            email.send()


@ignore_warnings(category=RemovedInDjango70Warning)
class DeprecatedCompatibilityTests(SimpleTestCase):
    def test_bad_header_error(self):
        """
        Existing code that catches deprecated BadHeaderError should be
        compatible with modern email (which raises ValueError instead).
        """
        from django.core.mail import BadHeaderError

        with self.assertRaises(BadHeaderError):
            EmailMessage(subject="Bad\r\nHeader").message()

    def test_attachments_mimebase_in_constructor(self):
        txt = MIMEText("content1")
        msg = EmailMessage(attachments=[txt])
        payload = msg.message().get_payload()
        self.assertEqual(payload[0], txt)


class DeprecatedEmailSettingsTests(SimpleTestCase):
    """Deprecations and compatibility errors related to EMAIL_PROVIDERS."""

    deprecated_setting_defaults = {
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "localhost",
        "EMAIL_PORT": 25,
        "EMAIL_HOST_USER": "",
        "EMAIL_HOST_PASSWORD": "",
        "EMAIL_USE_TLS": False,
        "EMAIL_USE_SSL": False,
        "EMAIL_SSL_CERTFILE": None,
        "EMAIL_SSL_KEYFILE": None,
        "EMAIL_TIMEOUT": None,
        # EMAIL_FILE_PATH does not have a default.
    }

    deprecated_settings = deprecated_setting_defaults.keys() | {"EMAIL_FILE_PATH"}

    # Many of these tests cover how django.conf.settings behaves at startup.
    #
    # To simulate that in a test case:
    # - Optionally use `with self.mock_settings_module(...):` to populate a
    #   simulated settings.py.
    # - Call self.init_simulated_settings() to initialize and return a local
    #   django.conf.settings-like object.
    #
    # (override_settings() goes through a different code path that does not
    # cover settings init, so cannot be used to verify deprecation warnings
    # or errors that should be issued at startup.)

    def mock_settings_module(self, **settings):
        settings_module = types.ModuleType("mocked_settings")
        for name, value in settings.items():
            setattr(settings_module, name, value)
        # Patch the settings module import in Settings.__init__() to
        # substitute the mocked settings.
        return mock.patch(
            "django.conf.importlib.import_module",
            autospec=True,
            return_value=settings_module,
        )

    def init_simulated_settings(self):
        settings = LazySettings()
        getattr(settings, "FOO", None)  # Trigger _setup().
        return settings

    def test_warn_when_defining_deprecated_settings(self):
        for name in self.deprecated_settings:
            msg = (
                f"The {name} setting is deprecated. Migrate to "
                "EMAIL_PROVIDERS before Django 7.0."
            )
            settings = {name: "foo"}
            with self.subTest(name=name):
                with (
                    self.subTest("settings module"),
                    self.mock_settings_module(**settings),
                    self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                ):
                    self.init_simulated_settings()
                with (
                    self.subTest("settings.configure()"),
                    self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                ):
                    LazySettings().configure(**settings)

        # Multiple deprecated settings are reported all at once.
        with self.subTest("multiple settings"):
            msg = (
                "The EMAIL_BACKEND, EMAIL_HOST settings are deprecated. "
                "Migrate to EMAIL_PROVIDERS before Django 7.0."
            )
            settings = {"EMAIL_BACKEND": "foo", "EMAIL_HOST": "bar"}
            with (
                self.subTest("settings module"),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                self.mock_settings_module(**settings),
            ):
                self.init_simulated_settings()
            with (
                self.subTest("settings.configure()"),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ):
                LazySettings().configure(**settings)

    def test_warn_email_providers_will_be_empty(self):
        msg = (
            "Django 7.0 will not have a default email provider. "
            "Define EMAIL_PROVIDERS in your settings to configure email."
        )
        with (
            self.subTest("settings module"),
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
        ):
            self.init_simulated_settings()

        with (
            self.subTest("settings.configure()"),
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
        ):
            LazySettings().configure()

    def test_no_warning_if_any_email_setting_defined(self):
        msg = "Django 7.0 will not have a default email provider."
        for name in self.deprecated_settings | {"EMAIL_PROVIDERS"}:
            with (
                self.subTest(name=name),
                self.mock_settings_module(**{name: "foo"}),
                # Use catch_warnings() to implement the equivalent of:
                #   self.assertNotWarnsMessage(msg, RemovedInDjango70Warning)
                warnings.catch_warnings(
                    category=RemovedInDjango70Warning, record=True
                ) as caught_warnings,
            ):
                # runtests.py filters this exact warning (to avoid it breaking
                # all tests). Undo that filter.
                warnings.simplefilter("always", category=RemovedInDjango70Warning)

                self.init_simulated_settings()

                warning_messages = [str(w.message) for w in caught_warnings or []]
                found = any(msg in w for w in warning_messages)
                self.assertFalse(found, f"{msg!r} was found in {warning_messages!r}.")

    def test_deprecated_settings_not_allowed_with_email_providers(self):
        for name in self.deprecated_settings:
            msg = (
                f"The deprecated {name} setting is not allowed when "
                "EMAIL_PROVIDERS is defined."
            )
            settings = {name: "foo", "EMAIL_PROVIDERS": {}}
            with self.subTest(name=name):
                with (
                    self.subTest("settings module"),
                    self.mock_settings_module(**settings),
                    self.assertRaisesMessage(ImproperlyConfigured, msg),
                ):
                    self.init_simulated_settings()
                with (
                    self.subTest("settings.configure()"),
                    self.assertRaisesMessage(ImproperlyConfigured, msg),
                ):
                    LazySettings().configure(**settings)

        # Multiple incompatible settings are reported all at once.
        with self.subTest("multiple settings"):
            msg = (
                "The deprecated EMAIL_BACKEND, EMAIL_HOST settings are not "
                "allowed when EMAIL_PROVIDERS is defined."
            )
            settings = {
                "EMAIL_BACKEND": "foo",
                "EMAIL_HOST": "bar",
                "EMAIL_PROVIDERS": {},
            }
            with (
                self.subTest("settings module"),
                self.assertRaisesMessage(ImproperlyConfigured, msg),
                self.mock_settings_module(**settings),
            ):
                self.init_simulated_settings()
            with (
                self.subTest("settings.configure()"),
                self.assertRaisesMessage(ImproperlyConfigured, msg),
            ):
                LazySettings().configure(**settings)

    def test_warn_when_using_deprecated_settings(self):
        for name in self.deprecated_settings:
            msg = (
                f"The {name} setting is deprecated. Migrate to "
                "EMAIL_PROVIDERS before Django 7.0."
            )
            with (
                self.subTest(name=name),
                self.settings(**{name: "foo"}),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ):
                getattr(settings, name)

    @override_settings(EMAIL_PROVIDERS={})
    def test_deprecated_settings_do_not_exist_when_email_providers_defined(self):
        # The global_settings defaults for the deprecated settings are hidden
        # when EMAIL_PROVIDERS is defined.
        for name in self.deprecated_settings:
            with self.subTest(name=name):
                self.assertFalse(hasattr(settings, name))

    @override_settings(EMAIL_PROVIDERS={})
    def test_deprecated_settings_not_in_dir_when_email_providers_defined(self):
        known_settings = dir(settings)
        actual_overlap = set(self.deprecated_settings) & set(known_settings)
        self.assertEqual(actual_overlap, set())

    def test_deprecated_settings_are_in_dir_without_email_providers(self):
        expected_settings = self.deprecated_setting_defaults.keys()
        known_settings = dir(settings)
        actual_overlap = set(expected_settings) & set(known_settings)
        self.assertEqual(actual_overlap, expected_settings)

    @override_settings(EMAIL_PROVIDERS={})
    def test_error_when_using_deprecated_settings_with_email_providers_defined(self):
        for name in self.deprecated_settings:
            msg = (
                f"The {name} setting is not available when EMAIL_PROVIDERS "
                "is defined"
            )
            with self.subTest(name=name), self.settings(**{name: "foo"}):
                with self.assertRaisesMessage(AttributeError, msg):
                    getattr(settings, name)

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_direct_settings_manipulation(self):
        settings = self.init_simulated_settings()

        # Accessing deprecated setting (from global defaults) caches its value
        # in LazySettings.__dir__.
        self.assertEqual(settings.EMAIL_PORT, 25)

        # Defining EMAIL_PROVIDERS invalidates the cache but is not an error.
        settings.EMAIL_PROVIDERS = {}

        # Accessing the conflicting setting _is_ an error.
        msg = "not available when EMAIL_PROVIDERS is defined"
        with self.assertRaisesMessage(AttributeError, msg):
            _ = settings.EMAIL_PORT  # Not `25` from the cache.

        # Adding a conflicting setting is not an error, but accessing it is.
        settings.EMAIL_HOST = "example.com"
        with self.assertRaisesMessage(AttributeError, msg):
            _ = settings.EMAIL_HOST

        # Deleting EMAIL_PROVIDERS removes the conflict and allows access to
        # the deprecated settings again.
        del settings.EMAIL_PROVIDERS
        self.assertEqual(settings.EMAIL_PORT, 25)
        self.assertEqual(settings.EMAIL_HOST, "example.com")

    @override_settings(EMAIL_PROVIDERS={})
    def test_error_when_using_conflicting_setting_via_override_settings(self):
        # Overriding EMAIL_HOST when EMAIL_PROVIDERS is defined creates a
        # conflict but does not cause an immediate error.
        with override_settings(EMAIL_HOST="example.com"):
            self.assertEqual(settings.EMAIL_PROVIDERS, {})
            # Trying to access the conflicting setting causes an error.
            with self.assertRaisesMessage(AttributeError, "not available"):
                _ = settings.EMAIL_HOST

            # The conflicting settings are both defined (neither is inherited
            # from default global_settings), so LazySettings.__dir__()
            # does not hide them.
            self.assertIn("EMAIL_HOST", dir(settings))
            self.assertIn("EMAIL_PROVIDERS", dir(settings))

            del settings.EMAIL_HOST
            self.assertNotIn("EMAIL_HOST", dir(settings))

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_deprecated_settings_defaults_unchanged(self):
        # Django's test runner overrides EMAIL_BACKEND in django.conf.settings,
        # so construct a fresh settings object for this test.
        settings = self.init_simulated_settings()
        for name, expected in self.deprecated_setting_defaults.items():
            with self.subTest(name=name):
                actual = getattr(settings, name)
                if expected is None:
                    self.assertIsNone(actual)
                elif expected is True or expected is False:
                    self.assertIs(actual, expected)
                else:
                    self.assertEqual(actual, expected)

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_email_backend_override_during_tests(self):
        self.assertEqual(
            settings.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend"
        )
