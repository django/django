# -*- coding:utf-8 -*-
from __future__ import unicode_literals

import logging
import warnings

from admin_scripts.tests import AdminScriptTestCase

from django.core import mail
from django.core.files.temp import NamedTemporaryFile
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import patch_logger
from django.utils.deprecation import RemovedInNextVersionWarning
from django.utils.encoding import force_text
from django.utils.log import (
    AdminEmailHandler, CallbackFilter, RequireDebugFalse, RequireDebugTrue,
)
from django.utils.six import StringIO

from .logconfig import MyEmailBackend

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


class LoggingFiltersTest(TestCase):
    def test_require_debug_false_filter(self):
        """
        Test the RequireDebugFalse filter class.
        """
        filter_ = RequireDebugFalse()

        with self.settings(DEBUG=True):
            self.assertEqual(filter_.filter("record is not used"), False)

        with self.settings(DEBUG=False):
            self.assertEqual(filter_.filter("record is not used"), True)

    def test_require_debug_true_filter(self):
        """
        Test the RequireDebugTrue filter class.
        """
        filter_ = RequireDebugTrue()

        with self.settings(DEBUG=True):
            self.assertEqual(filter_.filter("record is not used"), True)

        with self.settings(DEBUG=False):
            self.assertEqual(filter_.filter("record is not used"), False)


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


class WarningLoggerTests(TestCase):
    """
    Tests that warnings output for RemovedInDjangoXXWarning (XX being the next
    Django version) is enabled and captured to the logging system
    """
    def setUp(self):
        # If tests are invoke with "-Wall" (or any -W flag actually) then
        # warning logging gets disabled (see configure_logging in django/utils/log.py).
        # However, these tests expect warnings to be logged, so manually force warnings
        # to the logs. Use getattr() here because the logging capture state is
        # undocumented and (I assume) brittle.
        self._old_capture_state = bool(getattr(logging, '_warnings_showwarning', False))
        logging.captureWarnings(True)

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

        # Reset warnings state.
        logging.captureWarnings(self._old_capture_state)

    @override_settings(DEBUG=True)
    def test_warnings_capture(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('always')
            warnings.warn('Foo Deprecated', RemovedInNextVersionWarning)
            output = force_text(self.outputs[0].getvalue())
            self.assertIn('Foo Deprecated', output)

    def test_warnings_capture_debug_false(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('always')
            warnings.warn('Foo Deprecated', RemovedInNextVersionWarning)
            output = force_text(self.outputs[0].getvalue())
            self.assertNotIn('Foo Deprecated', output)

    @override_settings(DEBUG=True)
    def test_error_filter_still_raises(self):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                'error',
                category=RemovedInNextVersionWarning
            )
            with self.assertRaises(RemovedInNextVersionWarning):
                warnings.warn('Foo Deprecated', RemovedInNextVersionWarning)


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
        # Inspired from views/views.py: send_log()
        # ensuring the AdminEmailHandler does not get filtered out
        # even with DEBUG=True.
        admin_email_handler = [
            h for h in logger.handlers
            if h.__class__.__name__ == "AdminEmailHandler"
        ][0]
        return admin_email_handler

    def test_fail_silently(self):
        admin_email_handler = self.get_admin_email_handler(self.logger)
        self.assertTrue(admin_email_handler.connection().fail_silently)

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
        self.assertNotIn('\n', mail.outbox[0].subject)
        self.assertNotIn('\r', mail.outbox[0].subject)
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

    @override_settings(
        ADMINS=(('admin', 'admin@example.com'),),
        DEBUG=False,
    )
    def test_uses_custom_email_backend(self):
        """
        Refs #19325
        """
        message = 'All work and no play makes Jack a dull boy'
        admin_email_handler = self.get_admin_email_handler(self.logger)
        mail_admins_called = {'called': False}

        def my_mail_admins(*args, **kwargs):
            connection = kwargs['connection']
            self.assertIsInstance(connection, MyEmailBackend)
            mail_admins_called['called'] = True

        # Monkeypatches
        orig_mail_admins = mail.mail_admins
        orig_email_backend = admin_email_handler.email_backend
        mail.mail_admins = my_mail_admins
        admin_email_handler.email_backend = (
            'logging_tests.logconfig.MyEmailBackend')

        try:
            self.logger.error(message)
            self.assertTrue(mail_admins_called['called'])
        finally:
            # Revert Monkeypatches
            mail.mail_admins = orig_mail_admins
            admin_email_handler.email_backend = orig_email_backend

    @override_settings(
        ADMINS=(('whatever admin', 'admin@example.com'),),
    )
    def test_emit_non_ascii(self):
        """
        #23593 - AdminEmailHandler should allow Unicode characters in the
        request.
        """
        handler = self.get_admin_email_handler(self.logger)
        record = self.logger.makeRecord('name', logging.ERROR, 'function', 'lno', 'message', None, None)
        rf = RequestFactory()
        url_path = '/º'
        record.request = rf.get(url_path)
        handler.emit(record)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['admin@example.com'])
        self.assertEqual(msg.subject, "[Django] ERROR (EXTERNAL IP): message")
        self.assertIn("path:%s" % url_path, msg.body)

    @override_settings(
        MANAGERS=(('manager', 'manager@example.com'),),
        DEBUG=False,
    )
    def test_customize_send_mail_method(self):
        class ManagerEmailHandler(AdminEmailHandler):
            def send_mail(self, subject, message, *args, **kwargs):
                mail.mail_managers(subject, message, *args, connection=self.connection(), **kwargs)

        handler = ManagerEmailHandler()
        record = self.logger.makeRecord('name', logging.ERROR, 'function', 'lno', 'message', None, None)
        self.assertEqual(len(mail.outbox), 0)
        handler.emit(record)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['manager@example.com'])


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
        self.assertOutput(out, "System check identified no issues (0 silenced).")


def dictConfig(config):
    dictConfig.called = True
dictConfig.called = False


class SetupConfigureLogging(TestCase):
    """
    Test that calling django.setup() initializes the logging configuration.
    """
    @override_settings(LOGGING_CONFIG='logging_tests.tests.dictConfig',
                       LOGGING=OLD_LOGGING)
    def test_configure_initializes_logging(self):
        from django import setup
        setup()
        self.assertTrue(dictConfig.called)


@override_settings(DEBUG=True, ROOT_URLCONF='logging_tests.urls')
class SecurityLoggerTest(TestCase):

    def test_suspicious_operation_creates_log_message(self):
        with patch_logger('django.security.SuspiciousOperation', 'error') as calls:
            self.client.get('/suspicious/')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], 'dubious')

    def test_suspicious_operation_uses_sublogger(self):
        with patch_logger('django.security.DisallowedHost', 'error') as calls:
            self.client.get('/suspicious_spec/')
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], 'dubious')

    @override_settings(
        ADMINS=(('admin', 'admin@example.com'),),
        DEBUG=False,
    )
    def test_suspicious_email_admins(self):
        self.client.get('/suspicious/')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('path:/suspicious/,', mail.outbox[0].body)


class SettingsCustomLoggingTest(AdminScriptTestCase):
    """
    Test that using a logging defaults are still applied when using a custom
    callable in LOGGING_CONFIG (i.e., logging.config.fileConfig).
    """
    def setUp(self):
        logging_conf = """
[loggers]
keys=root
[handlers]
keys=stream
[formatters]
keys=simple
[logger_root]
handlers=stream
[handler_stream]
class=StreamHandler
formatter=simple
args=(sys.stdout,)
[formatter_simple]
format=%(message)s
"""
        self.temp_file = NamedTemporaryFile()
        self.temp_file.write(logging_conf.encode('utf-8'))
        self.temp_file.flush()
        sdict = {'LOGGING_CONFIG': '"logging.config.fileConfig"',
                 'LOGGING': 'r"%s"' % self.temp_file.name}
        self.write_settings('settings.py', sdict=sdict)

    def tearDown(self):
        self.temp_file.close()
        self.remove_settings('settings.py')

    def test_custom_logging(self):
        out, err = self.run_manage(['validate'])
        self.assertNoOutput(err)
        self.assertOutput(out, "System check identified no issues (0 silenced).")
