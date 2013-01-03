from __future__ import unicode_literals

import copy
import logging
import sys
import warnings

from django.conf import compat_patch_logging_config, LazySettings
from django.core import mail
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils.encoding import force_text
from django.utils.log import CallbackFilter, RequireDebugFalse
from django.utils.six import StringIO
from django.utils.unittest import skipUnless

from ..admin_scripts.tests import AdminScriptTestCase

PYVERS = sys.version_info[:2]

# logging config prior to using filter with mail_admins
OLD_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


class PatchLoggingConfigTest(TestCase):
    """
    Tests for backward-compat shim for #16288. These tests should be removed in
    Django 1.6 when that shim and DeprecationWarning are removed.

    """
    def test_filter_added(self):
        """
        Test that debug-false filter is added to mail_admins handler if it has
        no filters.

        """
        config = copy.deepcopy(OLD_LOGGING)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            compat_patch_logging_config(config)
            self.assertEqual(len(w), 1)

        self.assertEqual(
            config["handlers"]["mail_admins"]["filters"],
            ['require_debug_false'])

    def test_filter_configuration(self):
        """
        Test that the auto-added require_debug_false filter is an instance of
        `RequireDebugFalse` filter class.

        """
        config = copy.deepcopy(OLD_LOGGING)
        with warnings.catch_warnings(record=True):
            compat_patch_logging_config(config)

        flt = config["filters"]["require_debug_false"]
        self.assertEqual(flt["()"], "django.utils.log.RequireDebugFalse")

    def test_require_debug_false_filter(self):
        """
        Test the RequireDebugFalse filter class.

        """
        filter_ = RequireDebugFalse()

        with self.settings(DEBUG=True):
            self.assertEqual(filter_.filter("record is not used"), False)

        with self.settings(DEBUG=False):
            self.assertEqual(filter_.filter("record is not used"), True)

    def test_no_patch_if_filters_key_exists(self):
        """
        Test that the logging configuration is not modified if the mail_admins
        handler already has a "filters" key.

        """
        config = copy.deepcopy(OLD_LOGGING)
        config["handlers"]["mail_admins"]["filters"] = []
        new_config = copy.deepcopy(config)
        compat_patch_logging_config(new_config)

        self.assertEqual(config, new_config)

    def test_no_patch_if_no_mail_admins_handler(self):
        """
        Test that the logging configuration is not modified if the mail_admins
        handler is not present.

        """
        config = copy.deepcopy(OLD_LOGGING)
        config["handlers"].pop("mail_admins")
        new_config = copy.deepcopy(config)
        compat_patch_logging_config(new_config)

        self.assertEqual(config, new_config)


class DefaultLoggingTest(TestCase):
    def setUp(self):
        self.logger = logging.getLogger('django')
        self.old_stream = self.logger.handlers[0].stream

    def tearDown(self):
        self.logger.handlers[0].stream = self.old_stream

    def test_django_logger(self):
        """
        The 'django' base logger only output anything when DEBUG=True.
        """
        output = StringIO()
        self.logger.handlers[0].stream = output
        self.logger.error("Hey, this is an error.")
        self.assertEqual(output.getvalue(), '')

        with self.settings(DEBUG=True):
            self.logger.error("Hey, this is an error.")
            self.assertEqual(output.getvalue(), 'Hey, this is an error.\n')

@skipUnless(PYVERS > (2,6), "warnings captured only in Python >= 2.7")
class WarningLoggerTests(TestCase):
    """
    Tests that warnings output for DeprecationWarnings is enabled
    and captured to the logging system
    """
    def setUp(self):
        # this convoluted setup is to avoid printing this deprecation to
        # stderr during test running - as the test runner forces deprecations
        # to be displayed at the global py.warnings level
        self.logger = logging.getLogger('py.warnings')
        self.outputs = []
        self.old_streams = []
        for handler in self.logger.handlers:
            self.old_streams.append(handler.stream)
            self.outputs.append(StringIO())
            handler.stream = self.outputs[-1]

    def tearDown(self):
        for i, handler in enumerate(self.logger.handlers):
            self.logger.handlers[i].stream = self.old_streams[i]

    @override_settings(DEBUG=True)
    def test_warnings_capture(self):
        warnings.warn('Foo Deprecated', DeprecationWarning)
        output = force_text(self.outputs[0].getvalue())
        self.assertTrue('Foo Deprecated' in output)

    def test_warnings_capture_debug_false(self):
        warnings.warn('Foo Deprecated', DeprecationWarning)
        output = force_text(self.outputs[0].getvalue())
        self.assertFalse('Foo Deprecated' in output)


class CallbackFilterTest(TestCase):
    def test_sense(self):
        f_false = CallbackFilter(lambda r: False)
        f_true = CallbackFilter(lambda r: True)

        self.assertEqual(f_false.filter("record"), False)
        self.assertEqual(f_true.filter("record"), True)

    def test_passes_on_record(self):
        collector = []

        def _callback(record):
            collector.append(record)
            return True
        f = CallbackFilter(_callback)

        f.filter("a record")

        self.assertEqual(collector, ["a record"])


class AdminEmailHandlerTest(TestCase):
    logger = logging.getLogger('django.request')

    def get_admin_email_handler(self, logger):
        # Inspired from regressiontests/views/views.py: send_log()
        # ensuring the AdminEmailHandler does not get filtered out
        # even with DEBUG=True.
        admin_email_handler = [
            h for h in logger.handlers
            if h.__class__.__name__ == "AdminEmailHandler"
            ][0]
        return admin_email_handler

    @override_settings(
            ADMINS=(('whatever admin', 'admin@example.com'),),
            EMAIL_SUBJECT_PREFIX='-SuperAwesomeSubject-'
        )
    def test_accepts_args(self):
        """
        Ensure that user-supplied arguments and the EMAIL_SUBJECT_PREFIX
        setting are used to compose the email subject.
        Refs #16736.
        """
        message = "Custom message that says '%s' and '%s'"
        token1 = 'ping'
        token2 = 'pong'

        admin_email_handler = self.get_admin_email_handler(self.logger)
        # Backup then override original filters
        orig_filters = admin_email_handler.filters
        try:
            admin_email_handler.filters = []

            self.logger.error(message, token1, token2)

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, ['admin@example.com'])
            self.assertEqual(mail.outbox[0].subject,
                             "-SuperAwesomeSubject-ERROR: Custom message that says 'ping' and 'pong'")
        finally:
            # Restore original filters
            admin_email_handler.filters = orig_filters

    @override_settings(
            ADMINS=(('whatever admin', 'admin@example.com'),),
            EMAIL_SUBJECT_PREFIX='-SuperAwesomeSubject-',
            INTERNAL_IPS=('127.0.0.1',),
        )
    def test_accepts_args_and_request(self):
        """
        Ensure that the subject is also handled if being
        passed a request object.
        """
        message = "Custom message that says '%s' and '%s'"
        token1 = 'ping'
        token2 = 'pong'

        admin_email_handler = self.get_admin_email_handler(self.logger)
        # Backup then override original filters
        orig_filters = admin_email_handler.filters
        try:
            admin_email_handler.filters = []
            rf = RequestFactory()
            request = rf.get('/')
            self.logger.error(message, token1, token2,
                extra={
                    'status_code': 403,
                    'request': request,
                }
            )
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, ['admin@example.com'])
            self.assertEqual(mail.outbox[0].subject,
                             "-SuperAwesomeSubject-ERROR (internal IP): Custom message that says 'ping' and 'pong'")
        finally:
            # Restore original filters
            admin_email_handler.filters = orig_filters

    @override_settings(
            ADMINS=(('admin', 'admin@example.com'),),
            EMAIL_SUBJECT_PREFIX='',
            DEBUG=False,
        )
    def test_subject_accepts_newlines(self):
        """
        Ensure that newlines in email reports' subjects are escaped to avoid
        AdminErrorHandler to fail.
        Refs #17281.
        """
        message = 'Message \r\n with newlines'
        expected_subject = 'ERROR: Message \\r\\n with newlines'

        self.assertEqual(len(mail.outbox), 0)

        self.logger.error(message)

        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse('\n' in mail.outbox[0].subject)
        self.assertFalse('\r' in mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].subject, expected_subject)

    @override_settings(
            ADMINS=(('admin', 'admin@example.com'),),
            EMAIL_SUBJECT_PREFIX='',
            DEBUG=False,
        )
    def test_truncate_subject(self):
        """
        RFC 2822's hard limit is 998 characters per line.
        So, minus "Subject: ", the actual subject must be no longer than 989
        characters.
        Refs #17281.
        """
        message = 'a' * 1000
        expected_subject = 'ERROR: aa' + 'a' * 980

        self.assertEqual(len(mail.outbox), 0)

        self.logger.error(message)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, expected_subject)


class SettingsConfigTest(AdminScriptTestCase):
    """
    Test that accessing settings in a custom logging handler does not trigger
    a circular import error.
    """
    def setUp(self):
        log_config = """{
    'version': 1,
    'handlers': {
        'custom_handler': {
            'level': 'INFO',
            'class': 'logging_tests.logconfig.MyHandler',
        }
    }
}"""
        self.write_settings('settings.py', sdict={'LOGGING': log_config})

    def tearDown(self):
        self.remove_settings('settings.py')

    def test_circular_dependency(self):
        # validate is just an example command to trigger settings configuration
        out, err = self.run_manage(['validate'])
        self.assertNoOutput(err)
        self.assertOutput(out, "0 errors found")


def dictConfig(config):
    dictConfig.called = True
dictConfig.called = False


class SettingsConfigureLogging(TestCase):
    """
    Test that calling settings.configure() initializes the logging
    configuration.
    """
    def test_configure_initializes_logging(self):
        settings = LazySettings()
        settings.configure(
            LOGGING_CONFIG='regressiontests.logging_tests.tests.dictConfig')
        self.assertTrue(dictConfig.called)
