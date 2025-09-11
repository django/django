import logging
from contextlib import contextmanager
from io import StringIO
from unittest import TestCase, mock

from admin_scripts.tests import AdminScriptTestCase

from django.conf import settings
from django.core import mail
from django.core.exceptions import DisallowedHost, PermissionDenied, SuspiciousOperation
from django.core.files.temp import NamedTemporaryFile
from django.core.management import color
from django.http import HttpResponse
from django.http.multipartparser import MultiPartParserError
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.test.utils import LoggingCaptureMixin
from django.utils.log import (
    DEFAULT_LOGGING,
    AdminEmailHandler,
    CallbackFilter,
    RequireDebugFalse,
    RequireDebugTrue,
    ServerFormatter,
    log_response,
)
from django.views.debug import ExceptionReporter

from . import views
from .logconfig import MyEmailBackend


class LoggingFiltersTest(SimpleTestCase):
    def test_require_debug_false_filter(self):
        """
        Test the RequireDebugFalse filter class.
        """
        filter_ = RequireDebugFalse()

        with self.settings(DEBUG=True):
            self.assertIs(filter_.filter("record is not used"), False)

        with self.settings(DEBUG=False):
            self.assertIs(filter_.filter("record is not used"), True)

    def test_require_debug_true_filter(self):
        """
        Test the RequireDebugTrue filter class.
        """
        filter_ = RequireDebugTrue()

        with self.settings(DEBUG=True):
            self.assertIs(filter_.filter("record is not used"), True)

        with self.settings(DEBUG=False):
            self.assertIs(filter_.filter("record is not used"), False)


class SetupDefaultLoggingMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.config.dictConfig(DEFAULT_LOGGING)
        cls.addClassCleanup(logging.config.dictConfig, settings.LOGGING)


class DefaultLoggingTests(
    SetupDefaultLoggingMixin, LoggingCaptureMixin, SimpleTestCase
):
    def test_django_logger(self):
        """
        The 'django' base logger only output anything when DEBUG=True.
        """
        self.logger.error("Hey, this is an error.")
        self.assertEqual(self.logger_output.getvalue(), "")

        with self.settings(DEBUG=True):
            self.logger.error("Hey, this is an error.")
            self.assertEqual(self.logger_output.getvalue(), "Hey, this is an error.\n")

    @override_settings(DEBUG=True)
    def test_django_logger_warning(self):
        self.logger.warning("warning")
        self.assertEqual(self.logger_output.getvalue(), "warning\n")

    @override_settings(DEBUG=True)
    def test_django_logger_info(self):
        self.logger.info("info")
        self.assertEqual(self.logger_output.getvalue(), "info\n")

    @override_settings(DEBUG=True)
    def test_django_logger_debug(self):
        self.logger.debug("debug")
        self.assertEqual(self.logger_output.getvalue(), "")


class LoggingAssertionMixin:

    def assertLogRecord(
        self,
        logger_cm,
        msg,
        levelno,
        status_code,
        request=None,
        exc_class=None,
    ):
        self.assertEqual(
            records_len := len(logger_cm.records),
            1,
            f"Wrong number of calls for {logger_cm=} in {levelno=} (expected 1, got "
            f"{records_len}).",
        )
        record = logger_cm.records[0]
        self.assertEqual(record.getMessage(), msg)
        self.assertEqual(record.levelno, levelno)
        self.assertEqual(record.status_code, status_code)
        if request is not None:
            self.assertEqual(record.request, request)
        if exc_class:
            self.assertIsNotNone(record.exc_info)
            self.assertEqual(record.exc_info[0], exc_class)
        return record

    def assertLogsRequest(
        self, url, level, msg, status_code, logger="django.request", exc_class=None
    ):
        with self.assertLogs(logger, level) as cm:
            try:
                self.client.get(url)
            except views.UncaughtException:
                pass
            self.assertLogRecord(
                cm, msg, getattr(logging, level), status_code, exc_class=exc_class
            )


@override_settings(DEBUG=True, ROOT_URLCONF="logging_tests.urls")
class HandlerLoggingTests(
    SetupDefaultLoggingMixin, LoggingAssertionMixin, LoggingCaptureMixin, SimpleTestCase
):
    def test_page_found_no_warning(self):
        self.client.get("/innocent/")
        self.assertEqual(self.logger_output.getvalue(), "")

    def test_redirect_no_warning(self):
        self.client.get("/redirect/")
        self.assertEqual(self.logger_output.getvalue(), "")

    def test_page_not_found_warning(self):
        self.assertLogsRequest(
            url="/does_not_exist/",
            level="WARNING",
            status_code=404,
            msg="Not Found: /does_not_exist/",
        )

    def test_control_chars_escaped(self):
        self.assertLogsRequest(
            url="/%1B[1;31mNOW IN RED!!!1B[0m/",
            level="WARNING",
            status_code=404,
            msg=r"Not Found: /\x1b[1;31mNOW IN RED!!!1B[0m/",
        )

    async def test_async_page_not_found_warning(self):
        with self.assertLogs("django.request", "WARNING") as cm:
            await self.async_client.get("/does_not_exist/")

        self.assertLogRecord(cm, "Not Found: /does_not_exist/", logging.WARNING, 404)

    async def test_async_control_chars_escaped(self):
        with self.assertLogs("django.request", "WARNING") as cm:
            await self.async_client.get(r"/%1B[1;31mNOW IN RED!!!1B[0m/")

        self.assertLogRecord(
            cm, r"Not Found: /\x1b[1;31mNOW IN RED!!!1B[0m/", logging.WARNING, 404
        )

    def test_page_not_found_raised(self):
        self.assertLogsRequest(
            url="/does_not_exist_raised/",
            level="WARNING",
            status_code=404,
            msg="Not Found: /does_not_exist_raised/",
        )

    def test_uncaught_exception(self):
        self.assertLogsRequest(
            url="/uncaught_exception/",
            level="ERROR",
            status_code=500,
            msg="Internal Server Error: /uncaught_exception/",
            exc_class=views.UncaughtException,
        )

    def test_internal_server_error(self):
        self.assertLogsRequest(
            url="/internal_server_error/",
            level="ERROR",
            status_code=500,
            msg="Internal Server Error: /internal_server_error/",
        )

    def test_internal_server_error_599(self):
        self.assertLogsRequest(
            url="/internal_server_error/?status=599",
            level="ERROR",
            status_code=599,
            msg="Unknown Status Code: /internal_server_error/",
        )

    def test_permission_denied(self):
        self.assertLogsRequest(
            url="/permission_denied/",
            level="WARNING",
            status_code=403,
            msg="Forbidden (Permission denied): /permission_denied/",
            exc_class=PermissionDenied,
        )

    def test_multi_part_parser_error(self):
        self.assertLogsRequest(
            url="/multi_part_parser_error/",
            level="WARNING",
            status_code=400,
            msg="Bad request (Unable to parse request body): /multi_part_parser_error/",
            exc_class=MultiPartParserError,
        )


@override_settings(
    DEBUG=True,
    USE_I18N=True,
    LANGUAGES=[("en", "English")],
    MIDDLEWARE=[
        "django.middleware.locale.LocaleMiddleware",
        "django.middleware.common.CommonMiddleware",
    ],
    ROOT_URLCONF="logging_tests.urls_i18n",
)
class I18nLoggingTests(SetupDefaultLoggingMixin, LoggingCaptureMixin, SimpleTestCase):
    def test_i18n_page_found_no_warning(self):
        self.client.get("/exists/")
        self.client.get("/en/exists/")
        self.assertEqual(self.logger_output.getvalue(), "")

    def test_i18n_page_not_found_warning(self):
        self.client.get("/this_does_not/")
        self.client.get("/en/nor_this/")
        self.assertEqual(
            self.logger_output.getvalue(),
            "Not Found: /this_does_not/\nNot Found: /en/nor_this/\n",
        )


class CallbackFilterTest(SimpleTestCase):
    def test_sense(self):
        f_false = CallbackFilter(lambda r: False)
        f_true = CallbackFilter(lambda r: True)

        self.assertFalse(f_false.filter("record"))
        self.assertTrue(f_true.filter("record"))

    def test_passes_on_record(self):
        collector = []

        def _callback(record):
            collector.append(record)
            return True

        f = CallbackFilter(_callback)

        f.filter("a record")

        self.assertEqual(collector, ["a record"])


class AdminEmailHandlerTest(SimpleTestCase):
    logger = logging.getLogger("django")
    request_factory = RequestFactory()

    def get_admin_email_handler(self, logger):
        # AdminEmailHandler does not get filtered out
        # even with DEBUG=True.
        return [
            h for h in logger.handlers if h.__class__.__name__ == "AdminEmailHandler"
        ][0]

    def test_fail_silently(self):
        admin_email_handler = self.get_admin_email_handler(self.logger)
        self.assertTrue(admin_email_handler.connection().fail_silently)

    @override_settings(
        ADMINS=["admin@example.com"],
        EMAIL_SUBJECT_PREFIX="-SuperAwesomeSubject-",
    )
    def test_accepts_args(self):
        """
        User-supplied arguments and the EMAIL_SUBJECT_PREFIX setting are used
        to compose the email subject (#16736).
        """
        message = "Custom message that says '%s' and '%s'"
        token1 = "ping"
        token2 = "pong"

        admin_email_handler = self.get_admin_email_handler(self.logger)
        # Backup then override original filters
        orig_filters = admin_email_handler.filters
        try:
            admin_email_handler.filters = []

            self.logger.error(message, token1, token2)

            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
            self.assertEqual(
                mail.outbox[0].subject,
                "-SuperAwesomeSubject-ERROR: "
                "Custom message that says 'ping' and 'pong'",
            )
        finally:
            # Restore original filters
            admin_email_handler.filters = orig_filters

    @override_settings(
        ADMINS=["admin@example.com"],
        EMAIL_SUBJECT_PREFIX="-SuperAwesomeSubject-",
        INTERNAL_IPS=["127.0.0.1"],
    )
    def test_accepts_args_and_request(self):
        """
        The subject is also handled if being passed a request object.
        """
        message = "Custom message that says '%s' and '%s'"
        token1 = "ping"
        token2 = "pong"

        admin_email_handler = self.get_admin_email_handler(self.logger)
        # Backup then override original filters
        orig_filters = admin_email_handler.filters
        try:
            admin_email_handler.filters = []
            request = self.request_factory.get("/")
            self.logger.error(
                message,
                token1,
                token2,
                extra={
                    "status_code": 403,
                    "request": request,
                },
            )
            self.assertEqual(len(mail.outbox), 1)
            self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
            self.assertEqual(
                mail.outbox[0].subject,
                "-SuperAwesomeSubject-ERROR (internal IP): "
                "Custom message that says 'ping' and 'pong'",
            )
        finally:
            # Restore original filters
            admin_email_handler.filters = orig_filters

    @override_settings(
        ADMINS=["admin@example.com"],
        EMAIL_SUBJECT_PREFIX="",
        DEBUG=False,
    )
    def test_subject_accepts_newlines(self):
        """
        Newlines in email reports' subjects are escaped to prevent
        AdminErrorHandler from failing (#17281).
        """
        message = "Message \r\n with newlines"
        expected_subject = "ERROR: Message \\r\\n with newlines"

        self.assertEqual(len(mail.outbox), 0)

        self.logger.error(message)

        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("\n", mail.outbox[0].subject)
        self.assertNotIn("\r", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].subject, expected_subject)

    @override_settings(
        ADMINS=["admin@example.com"],
        DEBUG=False,
    )
    def test_uses_custom_email_backend(self):
        """
        Refs #19325
        """
        message = "All work and no play makes Jack a dull boy"
        admin_email_handler = self.get_admin_email_handler(self.logger)
        mail_admins_called = {"called": False}

        def my_mail_admins(*args, **kwargs):
            connection = kwargs["connection"]
            self.assertIsInstance(connection, MyEmailBackend)
            mail_admins_called["called"] = True

        # Monkeypatches
        orig_mail_admins = mail.mail_admins
        orig_email_backend = admin_email_handler.email_backend
        mail.mail_admins = my_mail_admins
        admin_email_handler.email_backend = "logging_tests.logconfig.MyEmailBackend"

        try:
            self.logger.error(message)
            self.assertTrue(mail_admins_called["called"])
        finally:
            # Revert Monkeypatches
            mail.mail_admins = orig_mail_admins
            admin_email_handler.email_backend = orig_email_backend

    @override_settings(
        ADMINS=["admin@example.com"],
    )
    def test_emit_non_ascii(self):
        """
        #23593 - AdminEmailHandler should allow Unicode characters in the
        request.
        """
        handler = self.get_admin_email_handler(self.logger)
        record = self.logger.makeRecord(
            "name", logging.ERROR, "function", "lno", "message", None, None
        )
        url_path = "/º"
        record.request = self.request_factory.get(url_path)
        handler.emit(record)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ["admin@example.com"])
        self.assertEqual(msg.subject, "[Django] ERROR (EXTERNAL IP): message")
        self.assertIn("Report at %s" % url_path, msg.body)

    @override_settings(
        MANAGERS=["manager@example.com"],
        DEBUG=False,
    )
    def test_customize_send_mail_method(self):
        class ManagerEmailHandler(AdminEmailHandler):
            def send_mail(self, subject, message, *args, **kwargs):
                mail.mail_managers(
                    subject, message, *args, connection=self.connection(), **kwargs
                )

        handler = ManagerEmailHandler()
        record = self.logger.makeRecord(
            "name", logging.ERROR, "function", "lno", "message", None, None
        )
        self.assertEqual(len(mail.outbox), 0)
        handler.emit(record)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["manager@example.com"])

    @override_settings(ALLOWED_HOSTS="example.com")
    def test_disallowed_host_doesnt_crash(self):
        admin_email_handler = self.get_admin_email_handler(self.logger)
        old_include_html = admin_email_handler.include_html

        # Text email
        admin_email_handler.include_html = False
        try:
            self.client.get("/", headers={"host": "evil.com"})
        finally:
            admin_email_handler.include_html = old_include_html

        # HTML email
        admin_email_handler.include_html = True
        try:
            self.client.get("/", headers={"host": "evil.com"})
        finally:
            admin_email_handler.include_html = old_include_html

    def test_default_exception_reporter_class(self):
        admin_email_handler = self.get_admin_email_handler(self.logger)
        self.assertEqual(admin_email_handler.reporter_class, ExceptionReporter)

    @override_settings(ADMINS=["admin@example.com"])
    def test_custom_exception_reporter_is_used(self):
        record = self.logger.makeRecord(
            "name", logging.ERROR, "function", "lno", "message", None, None
        )
        record.request = self.request_factory.get("/")
        handler = AdminEmailHandler(
            reporter_class="logging_tests.logconfig.CustomExceptionReporter"
        )
        handler.emit(record)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.body, "message\n\ncustom traceback text")

    @override_settings(ADMINS=["admin@example.com"])
    def test_emit_no_form_tag(self):
        """HTML email doesn't contain forms."""
        handler = AdminEmailHandler(include_html=True)
        record = self.logger.makeRecord(
            "name",
            logging.ERROR,
            "function",
            "lno",
            "message",
            None,
            None,
        )
        handler.emit(record)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, "[Django] ERROR: message")
        self.assertEqual(len(msg.alternatives), 1)
        body_html = str(msg.alternatives[0].content)
        self.assertIn('<div id="traceback">', body_html)
        self.assertNotIn("<form", body_html)

    @override_settings(ADMINS=[])
    def test_emit_no_admins(self):
        handler = AdminEmailHandler()
        record = self.logger.makeRecord(
            "name",
            logging.ERROR,
            "function",
            "lno",
            "message",
            None,
            None,
        )
        with mock.patch.object(
            handler,
            "format_subject",
            side_effect=AssertionError("Should not be called"),
        ):
            handler.emit(record)
        self.assertEqual(len(mail.outbox), 0)


class SettingsConfigTest(AdminScriptTestCase):
    """
    Accessing settings in a custom logging handler does not trigger
    a circular import error.
    """

    def setUp(self):
        super().setUp()
        log_config = """{
    'version': 1,
    'handlers': {
        'custom_handler': {
            'level': 'INFO',
            'class': 'logging_tests.logconfig.MyHandler',
        }
    }
}"""
        self.write_settings("settings.py", sdict={"LOGGING": log_config})

    def test_circular_dependency(self):
        # validate is just an example command to trigger settings configuration
        out, err = self.run_manage(["check"])
        self.assertNoOutput(err)
        self.assertOutput(out, "System check identified no issues (0 silenced).")


def dictConfig(config):
    dictConfig.called = True


dictConfig.called = False


class SetupConfigureLogging(SimpleTestCase):
    """
    Calling django.setup() initializes the logging configuration.
    """

    def test_configure_initializes_logging(self):
        from django import setup

        try:
            with override_settings(
                LOGGING_CONFIG="logging_tests.tests.dictConfig",
            ):
                setup()
        finally:
            # Restore logging from settings.
            setup()
        self.assertTrue(dictConfig.called)


@override_settings(DEBUG=True, ROOT_URLCONF="logging_tests.urls")
class SecurityLoggerTest(LoggingAssertionMixin, SimpleTestCase):
    def test_suspicious_operation_creates_log_message(self):
        self.assertLogsRequest(
            url="/suspicious/",
            level="ERROR",
            msg="dubious",
            status_code=400,
            logger="django.security.SuspiciousOperation",
            exc_class=SuspiciousOperation,
        )

    def test_suspicious_operation_uses_sublogger(self):
        self.assertLogsRequest(
            url="/suspicious_spec/",
            level="ERROR",
            msg="dubious",
            status_code=400,
            logger="django.security.DisallowedHost",
            exc_class=DisallowedHost,
        )

    @override_settings(
        ADMINS=["admin@example.com"],
        DEBUG=False,
    )
    def test_suspicious_email_admins(self):
        self.client.get("/suspicious/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("SuspiciousOperation at /suspicious/", mail.outbox[0].body)

    def test_response_logged(self):
        with self.assertLogs("django.security.SuspiciousOperation", "ERROR") as handler:
            response = self.client.get("/suspicious/")

        self.assertLogRecord(
            handler, "dubious", logging.ERROR, 400, request=response.wsgi_request
        )
        self.assertEqual(response.status_code, 400)


class SettingsCustomLoggingTest(AdminScriptTestCase):
    """
    Using a logging defaults are still applied when using a custom
    callable in LOGGING_CONFIG (i.e., logging.config.fileConfig).
    """

    def setUp(self):
        super().setUp()
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
        temp_file = NamedTemporaryFile()
        temp_file.write(logging_conf.encode())
        temp_file.flush()
        self.addCleanup(temp_file.close)
        self.write_settings(
            "settings.py",
            sdict={
                "LOGGING_CONFIG": '"logging.config.fileConfig"',
                "LOGGING": 'r"%s"' % temp_file.name,
            },
        )

    def test_custom_logging(self):
        out, err = self.run_manage(["check"])
        self.assertNoOutput(err)
        self.assertOutput(out, "System check identified no issues (0 silenced).")


class LogFormattersTests(SimpleTestCase):
    def test_server_formatter_styles(self):
        color_style = color.make_style("")
        formatter = ServerFormatter()
        formatter.style = color_style
        log_msg = "log message"
        status_code_styles = [
            (200, "HTTP_SUCCESS"),
            (100, "HTTP_INFO"),
            (304, "HTTP_NOT_MODIFIED"),
            (300, "HTTP_REDIRECT"),
            (404, "HTTP_NOT_FOUND"),
            (400, "HTTP_BAD_REQUEST"),
            (500, "HTTP_SERVER_ERROR"),
        ]
        for status_code, style in status_code_styles:
            record = logging.makeLogRecord({"msg": log_msg, "status_code": status_code})
            self.assertEqual(
                formatter.format(record), getattr(color_style, style)(log_msg)
            )
        record = logging.makeLogRecord({"msg": log_msg})
        self.assertEqual(formatter.format(record), log_msg)

    def test_server_formatter_default_format(self):
        server_time = "2016-09-25 10:20:30"
        log_msg = "log message"
        logger = logging.getLogger("django.server")

        @contextmanager
        def patch_django_server_logger():
            old_stream = logger.handlers[0].stream
            new_stream = StringIO()
            logger.handlers[0].stream = new_stream
            yield new_stream
            logger.handlers[0].stream = old_stream

        with patch_django_server_logger() as logger_output:
            logger.info(log_msg, extra={"server_time": server_time})
            self.assertEqual(
                "[%s] %s\n" % (server_time, log_msg), logger_output.getvalue()
            )

        with patch_django_server_logger() as logger_output:
            logger.info(log_msg)
            self.assertRegex(
                logger_output.getvalue(), r"^\[[/:,\w\s\d]+\] %s\n" % log_msg
            )


class LogResponseRealLoggerTests(LoggingAssertionMixin, TestCase):

    request = RequestFactory().get("/test-path/")

    def test_missing_response_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            log_response("No response provided", response=None, request=self.request)

    def test_missing_request_logs_with_none(self):
        response = HttpResponse(status=403)
        with self.assertLogs("django.request", level="INFO") as cm:
            log_response(msg := "Missing request", response=response, request=None)
        self.assertLogRecord(cm, msg, logging.WARNING, 403, request=None)

    def test_logs_5xx_as_error(self):
        response = HttpResponse(status=508)
        with self.assertLogs("django.request", level="ERROR") as cm:
            log_response(
                msg := "Server error occurred", response=response, request=self.request
            )
        self.assertLogRecord(cm, msg, logging.ERROR, 508, self.request)

    def test_logs_4xx_as_warning(self):
        response = HttpResponse(status=418)
        with self.assertLogs("django.request", level="WARNING") as cm:
            log_response(
                msg := "This is a teapot!", response=response, request=self.request
            )
        self.assertLogRecord(cm, msg, logging.WARNING, 418, self.request)

    def test_logs_2xx_as_info(self):
        response = HttpResponse(status=201)
        with self.assertLogs("django.request", level="INFO") as cm:
            log_response(msg := "OK response", response=response, request=self.request)
        self.assertLogRecord(cm, msg, logging.INFO, 201, self.request)

    def test_custom_log_level(self):
        response = HttpResponse(status=403)
        with self.assertLogs("django.request", level="DEBUG") as cm:
            log_response(
                msg := "Debug level log",
                response=response,
                request=self.request,
                level="debug",
            )
        self.assertLogRecord(cm, msg, logging.DEBUG, 403, self.request)

    def test_logs_only_once_per_response(self):
        response = HttpResponse(status=500)
        with self.assertLogs("django.request", level="ERROR") as cm:
            log_response("First log", response=response, request=self.request)
            log_response("Second log", response=response, request=self.request)
        self.assertLogRecord(cm, "First log", logging.ERROR, 500, self.request)

    def test_exc_info_output(self):
        response = HttpResponse(status=500)
        try:
            raise ValueError("Simulated failure")
        except ValueError as exc:
            with self.assertLogs("django.request", level="ERROR") as cm:
                log_response(
                    "With exception",
                    response=response,
                    request=self.request,
                    exception=exc,
                )
        self.assertLogRecord(cm, "With exception", logging.ERROR, 500, self.request)
        self.assertIn("ValueError", "\n".join(cm.output))  # Stack trace included

    def test_format_args_are_applied(self):
        response = HttpResponse(status=500)
        with self.assertLogs("django.request", level="ERROR") as cm:
            log_response(
                "Something went wrong: %s (%d)",
                "DB error",
                42,
                response=response,
                request=self.request,
            )
        msg = "Something went wrong: DB error (42)"
        self.assertLogRecord(cm, msg, logging.ERROR, 500, self.request)

    def test_logs_with_custom_logger(self):
        handler = logging.StreamHandler(log_stream := StringIO())
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))

        custom_logger = logging.getLogger("my.custom.logger")
        custom_logger.setLevel(logging.DEBUG)
        custom_logger.addHandler(handler)
        self.addCleanup(custom_logger.removeHandler, handler)

        response = HttpResponse(status=404)
        log_response(
            msg := "Handled by custom logger",
            response=response,
            request=self.request,
            logger=custom_logger,
        )

        self.assertEqual(
            f"WARNING:my.custom.logger:{msg}", log_stream.getvalue().strip()
        )

    def test_unicode_escape_escaping(self):
        test_cases = [
            # Control characters.
            ("line\nbreak", "line\\nbreak"),
            ("carriage\rreturn", "carriage\\rreturn"),
            ("tab\tseparated", "tab\\tseparated"),
            ("formfeed\f", "formfeed\\x0c"),
            ("bell\a", "bell\\x07"),
            ("multi\nline\ntext", "multi\\nline\\ntext"),
            # Slashes.
            ("slash\\test", "slash\\\\test"),
            ("back\\slash", "back\\\\slash"),
            # Quotes.
            ('quote"test"', 'quote"test"'),
            ("quote'test'", "quote'test'"),
            # Accented, composed characters, emojis and symbols.
            ("café", "caf\\xe9"),
            ("e\u0301", "e\\u0301"),  # e + combining acute
            ("smile🙂", "smile\\U0001f642"),
            ("weird ☃️", "weird \\u2603\\ufe0f"),
            # Non-Latin alphabets.
            ("Привет", "\\u041f\\u0440\\u0438\\u0432\\u0435\\u0442"),
            ("你好", "\\u4f60\\u597d"),
            # ANSI escape sequences.
            ("escape\x1b[31mred\x1b[0m", "escape\\x1b[31mred\\x1b[0m"),
            (
                "/\x1b[1;31mCAUTION!!YOU ARE PWNED\x1b[0m/",
                "/\\x1b[1;31mCAUTION!!YOU ARE PWNED\\x1b[0m/",
            ),
            (
                "/\r\n\r\n1984-04-22 INFO    Listening on 0.0.0.0:8080\r\n\r\n",
                "/\\r\\n\\r\\n1984-04-22 INFO    Listening on 0.0.0.0:8080\\r\\n\\r\\n",
            ),
            # Plain safe input.
            ("normal-path", "normal-path"),
            ("slash/colon:", "slash/colon:"),
            # Non strings.
            (0, "0"),
            ([1, 2, 3], "[1, 2, 3]"),
            ({"test": "🙂"}, "{'test': '🙂'}"),
        ]

        msg = "Test message: %s"
        for case, expected in test_cases:
            with (
                self.assertLogs("django.request", level="ERROR") as cm,
                self.subTest(case=case),
            ):
                response = HttpResponse(status=318)
                log_response(msg, case, response=response, level="error")

                record = self.assertLogRecord(
                    cm,
                    msg % expected,
                    levelno=logging.ERROR,
                    status_code=318,
                    request=None,
                )
                # Log record is always a single line.
                self.assertEqual(len(record.getMessage().splitlines()), 1)
