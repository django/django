import logging
import sys
from io import StringIO
from unittest import mock

from django.test import SimpleTestCase
from django.test.runner import DiscoverRunner
from django.test.utils import captured_stdout


class CheckLoggerTests(SimpleTestCase):
    """Tests for DiscoverRunner._get_or_create_check_logger()."""

    def test_get_or_create_check_logger_creates_default(self):
        """
        _get_or_create_check_logger() should return a logger that routes
        messages through the logging system.
        """
        runner = DiscoverRunner()
        logger = runner._get_or_create_check_logger()

        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "django.test.check")
        self.assertEqual(logger.level, logging.INFO)
        self.assertFalse(logger.propagate)

    def test_get_or_create_check_logger_returns_custom_logger(self):
        """
        If a custom logger is provided to DiscoverRunner, it should be
        returned by _get_or_create_check_logger().
        """
        custom_logger = logging.getLogger("tests.custom_logger")
        runner = DiscoverRunner(logger=custom_logger)

        returned_logger = runner._get_or_create_check_logger()

        self.assertIs(returned_logger, custom_logger)

    def test_get_or_create_check_logger_idempotent(self):
        """
        _get_or_create_check_logger() should only configure handlers once.
        """
        runner = DiscoverRunner()
        logger1 = runner._get_or_create_check_logger()
        initial_handler_count = len(logger1.handlers)

        # Call again - should return the same logger
        logger2 = runner._get_or_create_check_logger()

        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger2.handlers), initial_handler_count)

    def test_check_formatter_info_no_prefix(self):
        """
        CheckFormatter should not add a prefix to INFO messages.
        """
        runner = DiscoverRunner()
        logger = runner._get_or_create_check_logger()
        formatter = logger.handlers[0].formatter

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Info message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        self.assertEqual(formatted, "Info message")

    def test_check_formatter_warning_with_prefix(self):
        """
        CheckFormatter should add [WARNING] prefix to warning messages.
        """
        runner = DiscoverRunner()
        logger = runner._get_or_create_check_logger()
        formatter = logger.handlers[0].formatter

        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        self.assertEqual(formatted, "[WARNING] Warning message")

    def test_check_formatter_error_with_prefix(self):
        """
        CheckFormatter should add [ERROR] prefix to error messages.
        """
        runner = DiscoverRunner()
        logger = runner._get_or_create_check_logger()
        formatter = logger.handlers[0].formatter

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        self.assertEqual(formatted, "[ERROR] Error message")


class RunChecksTests(SimpleTestCase):
    """Tests for DiscoverRunner.run_checks()."""

    def test_run_checks_without_logger_creates_default(self):
        """
        run_checks() without a logger should create a default logger and
        capture check command output.
        """
        runner = DiscoverRunner()

        # Patch call_command where it's used in runner module
        with mock.patch("django.test.runner.call_command") as mock_call:
            # Simulate check command printing to stdout
            def fake_check(*args, **kwargs):
                print("System check identified no issues (0 silenced).")

            mock_call.side_effect = fake_check

            # The logger writes to stdout, so capture it to verify
            with self.assertLogs("django.test.check", level=logging.INFO) as cm:
                runner.run_checks(databases=["default"])

            # Verify call_command was called with correct arguments
            mock_call.assert_called_once_with(
                "check",
                verbosity=runner.verbosity,
                databases=["default"],
            )

            # Verify output was logged
            self.assertIn(
                "System check identified no issues", cm.records[0].getMessage()
            )

    def test_run_checks_with_custom_logger(self):
        """
        run_checks() should use a custom logger if provided to DiscoverRunner.
        """
        custom_logger = logging.getLogger("tests.run_checks_custom")
        custom_logger.setLevel(logging.INFO)

        # Add handler to capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        custom_logger.addHandler(handler)
        self.addCleanup(custom_logger.removeHandler, handler)

        runner = DiscoverRunner(logger=custom_logger)

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                print("Check output from custom logger")

            mock_call.side_effect = fake_check

            runner.run_checks(databases=["default"])

        # Verify the custom logger received the output
        stream.seek(0)
        output = stream.read()
        self.assertIn("Check output from custom logger", output)

    def test_run_checks_logs_stdout_as_info(self):
        """
        Stdout output from check command should be logged at INFO level.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                print("Stdout message")

            mock_call.side_effect = fake_check

            with self.assertLogs("django.test.check", level=logging.INFO) as cm:
                runner.run_checks(databases=["default"])

            # Check that the message was logged at INFO level
            self.assertEqual(len(cm.records), 1)
            self.assertEqual(cm.records[0].levelname, "INFO")
            self.assertIn("Stdout message", cm.records[0].getMessage())

    def test_run_checks_logs_stderr_as_error(self):
        """
        Stderr output from check command should be logged at ERROR level.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                sys.stderr.write("Error message\n")

            mock_call.side_effect = fake_check

            with self.assertLogs("django.test.check", level=logging.ERROR) as cm:
                runner.run_checks(databases=["default"])

            # Check that the message was logged at ERROR level
            self.assertEqual(len(cm.records), 1)
            self.assertEqual(cm.records[0].levelname, "ERROR")
            self.assertIn("Error message", cm.records[0].getMessage())

    def test_run_checks_empty_stdout_not_logged(self):
        """
        Empty stdout should not result in a log message.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command"):
            # call_command doesn't print anything
            # Use captured_stdout to verify no output
            with captured_stdout() as stdout:
                runner.run_checks(databases=["default"])

            # There should be no output since nothing was printed
            self.assertEqual(stdout.getvalue(), "")

    def test_run_checks_empty_stderr_not_logged(self):
        """
        Empty stderr should not result in an error log message.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                print("Only stdout")

            mock_call.side_effect = fake_check

            with self.assertLogs("django.test.check", level=logging.INFO) as cm:
                runner.run_checks(databases=["default"])

            # Should only have INFO, no ERROR
            self.assertEqual(len(cm.records), 1)
            self.assertEqual(cm.records[0].levelname, "INFO")

    def test_run_checks_passes_databases_parameter(self):
        """
        run_checks() should pass the databases parameter to call_command.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:
            runner.run_checks(databases=["default", "other"])

            mock_call.assert_called_once()
            call_args = mock_call.call_args
            self.assertEqual(call_args[1]["databases"], ["default", "other"])

    def test_run_checks_passes_verbosity_parameter(self):
        """
        run_checks() should pass the runner's verbosity to call_command.
        """
        runner = DiscoverRunner(verbosity=2)

        with mock.patch("django.test.runner.call_command") as mock_call:
            runner.run_checks(databases=["default"])

            mock_call.assert_called_once()
            call_args = mock_call.call_args
            self.assertEqual(call_args[1]["verbosity"], 2)

    def test_run_checks_both_stdout_and_stderr(self):
        """
        run_checks() should handle both stdout and stderr output.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                print("Stdout output")
                sys.stderr.write("Stderr output\n")

            mock_call.side_effect = fake_check

            with self.assertLogs("django.test.check", level=logging.INFO) as cm:
                runner.run_checks(databases=["default"])

            # Should have both INFO and ERROR logs
            self.assertEqual(len(cm.records), 2)
            levels = {record.levelname for record in cm.records}
            self.assertEqual(levels, {"INFO", "ERROR"})

    def test_run_checks_strips_whitespace(self):
        """
        run_checks() should strip leading/trailing whitespace from output.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                print("\n  Message with whitespace  \n")

            mock_call.side_effect = fake_check

            with self.assertLogs("django.test.check", level=logging.INFO) as cm:
                runner.run_checks(databases=["default"])

            # Message should be stripped
            message = cm.records[0].getMessage()
            self.assertEqual(message, "Message with whitespace")

    def test_run_checks_multiline_output(self):
        """
        run_checks() should handle multiline output from check command.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command") as mock_call:

            def fake_check(*args, **kwargs):
                print("Line 1\nLine 2\nLine 3")

            mock_call.side_effect = fake_check

            with self.assertLogs("django.test.check", level=logging.INFO) as cm:
                runner.run_checks(databases=["default"])

            message = cm.records[0].getMessage()
            self.assertIn("Line 1", message)
            self.assertIn("Line 2", message)
            self.assertIn("Line 3", message)

    def test_run_checks_logger_reused_across_calls(self):
        """
        The logger should be reused across multiple run_checks() calls.
        """
        runner = DiscoverRunner()

        with mock.patch("django.test.runner.call_command"):
            runner.run_checks(databases=["default"])
            logger1 = runner.logger

            runner.run_checks(databases=["default"])
            logger2 = runner.logger

            self.assertIs(logger1, logger2)
