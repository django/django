# RemovedInDjango70Warning: This entire file.
import re
import types
import warnings
from contextlib import contextmanager
from email.mime.text import MIMEText
from unittest import mock

import django.conf
import django.utils.timezone
from django.conf import LazySettings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import (
    EmailAlternative,
    EmailAttachment,
    EmailMessage,
    EmailMultiAlternatives,
    get_connection,
    mailers,
)
from django.core.mail.deprecation import NO_DEFAULT_MAILER_WARNING
from django.core.mail.message import forbid_multi_line_headers, sanitize_address
from django.test import SimpleTestCase, ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango70Warning

from . import override_deprecated_email_settings
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
    """Deprecations and compatibility errors related to MAILERS."""

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

    # Tests for defining settings must cover three separate cases, which go
    # through different code paths in django.conf:
    # - settings module (settings.py; LazySettings wraps Settings)
    # - settings.configure() (LazySettings wraps UserSettingsHolder)
    # - override_settings() (a.k.a. SimpleTestCase.settings(); temporarily
    #   inserts a UserSettingsHolder into the current LazySettings)
    #
    # A settings module must be simulated in these tests. (The real settings
    # module can't be modified, and override_settings() isn't the same as using
    # a settings module.) To do that:
    # - Optionally use a self.mock_settings_module() context to populate a
    #   simulated settings.py.
    # - Call self.init_simulated_settings() to initialize settings from a
    #   module (the mock_settings_module() if active, else the real one) and
    #   return a settings object equivalent to django.conf.settings.

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
        # Trigger LazySettings._setup() *from within Django*. (In real use,
        # the first settings access is often iter(db.connections) in
        # run_checks() or similar. But any settings access will work, and
        # it's hard to mock db.connections due to @cached_property() usage.)
        with mock.patch.object(django.utils.timezone, "settings", settings):
            django.utils.timezone.now()  # Reads settings.USE_TZ.
        return settings

    @contextmanager
    def assertNotWarnsMessage(self, category, message):
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.filterwarnings(
                "always", category=category, message=rf".*{re.escape(message)}"
            )
            yield caught_warnings
        self.assertEqual([str(warning) for warning in caught_warnings], [])

    def assertHasOnlyDefaultEmailSettings(self, settings, msg=None):
        non_default_settings = [
            name for name in self.deprecated_settings if settings.is_overridden(name)
        ]
        if hasattr(settings, "MAILERS"):
            non_default_settings.append("MAILERS")
        self.assertEqual(non_default_settings, [], msg=msg)

    def test_warn_when_defining_deprecated_settings(self):
        for name in self.deprecated_settings:
            msg = (
                f"The {name} setting is deprecated. Migrate to "
                "MAILERS before Django 7.0."
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
                with (
                    self.subTest("override_settings()"),
                    self.assertWarnsMessage(RemovedInDjango70Warning, msg),
                ):
                    with override_settings(**settings):
                        pass

    def test_multiple_deprecated_settings_are_all_reported(self):
        msg_re = r"The EMAIL_(BACKEND|HOST|PORT) setting is deprecated."
        settings = {"EMAIL_BACKEND": "foo", "EMAIL_HOST": "bar", "EMAIL_PORT": 2525}
        expected_warning_count = len(settings)

        with self.subTest("settings module"), self.mock_settings_module(**settings):
            with self.assertWarnsRegex(RemovedInDjango70Warning, msg_re) as cm:
                self.init_simulated_settings()
            self.assertEqual(len(cm.warnings), expected_warning_count)

        with self.subTest("settings.configure()"):
            with self.assertWarnsRegex(RemovedInDjango70Warning, msg_re) as cm:
                LazySettings().configure(**settings)
            self.assertEqual(len(cm.warnings), expected_warning_count)

        with self.subTest("override_settings()"):
            with (
                self.assertWarnsRegex(RemovedInDjango70Warning, msg_re) as cm,
                override_settings(**settings),
            ):
                pass
            # override_settings() accesses each setting twice: setattr while
            # enabling and getattr while disabling (for change notification).
            self.assertEqual(len(cm.warnings), 2 * expected_warning_count)

    def test_warn_about_no_default_mailer(self):
        # Test precondition: the real settings object must be default.
        self.assertHasOnlyDefaultEmailSettings(django.conf.settings)

        # The warning is issued if no email-backend-related settings are
        # defined, but only when email is sent. Any attempt to send email
        # should invoke get_connection() or mailers.create_connection().
        msg = NO_DEFAULT_MAILER_WARNING
        with (
            self.subTest("get_connection()"),
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ignore_warnings(
                category=RemovedInDjango70Warning,
                message=re.escape("get_connection() is deprecated."),
            ),
        ):
            get_connection()
        with (
            self.subTest("mailers.default"),
            self.assertWarnsMessage(RemovedInDjango70Warning, msg),
        ):
            _ = mailers.default

        # The warning is not issued on startup, to avoid creating noise for
        # projects that don't send email at all.
        with self.assertNotWarnsMessage(RemovedInDjango70Warning, msg):
            settings = self.init_simulated_settings()
        self.assertHasOnlyDefaultEmailSettings(settings, msg="invalid test")

    def test_no_default_mailer_warning_if_any_email_setting_defined(self):
        # Test precondition: the real settings object must be default.
        self.assertHasOnlyDefaultEmailSettings(django.conf.settings)

        # The warning from the previous test is not issued if any deprecated
        # email setting is defined (which would result in a startup-time
        # warning about MAILERS) or if MAILERS is defined.
        msg = NO_DEFAULT_MAILER_WARNING
        for name in self.deprecated_settings:
            value = self.deprecated_setting_defaults.get(name, "foo")
            with (
                self.subTest(name=name),
                override_deprecated_email_settings(**{name: value}),
                self.assertNotWarnsMessage(RemovedInDjango70Warning, msg),
            ):
                _ = mailers.default
        with (
            self.subTest(name="MAILERS"),
            self.settings(
                MAILERS={
                    "default": {
                        "BACKEND": "django.core.mail.backends.locmem.EmailBackend"
                    }
                }
            ),
            self.assertNotWarnsMessage(RemovedInDjango70Warning, msg),
        ):
            _ = mailers.default

    def test_deprecated_settings_not_allowed_with_mailers(self):
        for name in self.deprecated_settings:
            msg = (
                "Deprecated email settings are not allowed when "
                f"MAILERS is defined: {name}."
            )
            settings = {name: "foo", "MAILERS": {}}
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
                # There is intentionally no override_settings() subtest here.
                # override_settings() does not check for settings conflicts.

    def test_warn_when_using_deprecated_settings(self):
        for name in self.deprecated_settings:
            msg = (
                f"The {name} setting is deprecated. Migrate to "
                "MAILERS before Django 7.0."
            )
            with (
                self.subTest(name=name),
                override_deprecated_email_settings(**{name: "foo"}),
                self.assertWarnsMessage(RemovedInDjango70Warning, msg),
            ):
                getattr(django.conf.settings, name)

    @override_settings(MAILERS={})
    def test_deprecated_settings_do_not_exist_when_mailers_defined(self):
        # The global_settings defaults for the deprecated settings are hidden
        # when MAILERS is defined.
        for name in self.deprecated_settings:
            with self.subTest(name=name):
                self.assertFalse(hasattr(django.conf.settings, name))

    @override_settings(MAILERS={})
    def test_deprecated_settings_not_in_dir_when_mailers_defined(self):
        known_settings = dir(django.conf.settings)
        actual_overlap = set(self.deprecated_settings) & set(known_settings)
        self.assertEqual(actual_overlap, set())

    def test_deprecated_settings_are_in_dir_without_mailers(self):
        expected_settings = self.deprecated_setting_defaults.keys()
        known_settings = dir(django.conf.settings)
        actual_overlap = set(expected_settings) & set(known_settings)
        self.assertEqual(actual_overlap, expected_settings)

    @override_settings(MAILERS={})
    def test_error_when_using_deprecated_settings_with_mailers_defined(self):
        for name in self.deprecated_settings:
            msg = f"The {name} setting is not available when MAILERS is defined."
            with (
                self.subTest(name=name),
                override_deprecated_email_settings(**{name: "foo"}),
            ):
                with self.assertRaisesMessage(AttributeError, msg):
                    getattr(django.conf.settings, name)

    @ignore_warnings(category=RemovedInDjango70Warning)
    def test_direct_settings_manipulation(self):
        settings = self.init_simulated_settings()

        # Accessing deprecated setting (from global defaults) caches its value
        # in LazySettings.__dir__.
        self.assertEqual(settings.EMAIL_PORT, 25)

        # Defining MAILERS invalidates the cache but is not an error.
        settings.MAILERS = {}

        # Accessing the conflicting setting _is_ an error.
        msg = "not available when MAILERS is defined"
        with self.assertRaisesMessage(AttributeError, msg):
            _ = settings.EMAIL_PORT  # Not `25` from the cache.

        # Adding a conflicting setting is not an error, but accessing it is.
        settings.EMAIL_HOST = "example.com"
        with self.assertRaisesMessage(AttributeError, msg):
            _ = settings.EMAIL_HOST

        # Deleting MAILERS removes the conflict and allows access to
        # the deprecated settings again.
        del settings.MAILERS
        self.assertEqual(settings.EMAIL_PORT, 25)
        self.assertEqual(settings.EMAIL_HOST, "example.com")

    @override_settings(MAILERS={})
    def test_error_when_using_conflicting_setting_via_override_settings(self):
        # Overriding EMAIL_HOST when MAILERS is defined creates a
        # conflict but does not cause an immediate error.
        with override_deprecated_email_settings(EMAIL_HOST="example.com"):
            self.assertEqual(django.conf.settings.MAILERS, {})
            # Trying to access the conflicting setting causes an error.
            with self.assertRaisesMessage(AttributeError, "not available"):
                _ = django.conf.settings.EMAIL_HOST

            # Both conflicting settings are defined (neither is inherited from
            # default global_settings), so LazySettings.__dir__() does not hide
            # them.
            self.assertIn("EMAIL_HOST", dir(django.conf.settings))
            self.assertIn("MAILERS", dir(django.conf.settings))

            del django.conf.settings.EMAIL_HOST
            self.assertNotIn("EMAIL_HOST", dir(django.conf.settings))

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
            django.conf.settings.EMAIL_BACKEND,
            "django.core.mail.backends.locmem.EmailBackend",
        )
