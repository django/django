import copy

from django.conf import compat_patch_logging_config
from django.core import mail
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils.log import CallbackFilter, RequireDebugFalse, getLogger


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
        compat_patch_logging_config(config)

        self.assertEqual(
            config["handlers"]["mail_admins"]["filters"],
            ['require_debug_false'])

    def test_filter_configuration(self):
        """
        Test that the auto-added require_debug_false filter is an instance of
        `RequireDebugFalse` filter class.

        """
        config = copy.deepcopy(OLD_LOGGING)
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

        logger = getLogger('django.request')
        admin_email_handler = self.get_admin_email_handler(logger)
        # Backup then override original filters
        orig_filters = admin_email_handler.filters
        try:
            admin_email_handler.filters = []

            logger.error(message, token1, token2)

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

        logger = getLogger('django.request')
        admin_email_handler = self.get_admin_email_handler(logger)
        # Backup then override original filters
        orig_filters = admin_email_handler.filters
        try:
            admin_email_handler.filters = []
            rf = RequestFactory()
            request = rf.get('/')
            logger.error(message, token1, token2,
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
        message = u'Message \r\n with newlines'
        expected_subject = u'ERROR: Message \\r\\n with newlines'

        self.assertEqual(len(mail.outbox), 0)

        logger = getLogger('django.request')
        logger.error(message)

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

        logger = getLogger('django.request')
        logger.error(message)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, expected_subject)
