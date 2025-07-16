import logging
import unittest
from io import StringIO
from time import time
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.test import TestCase
from django.test.runner import DiscoverRunner, QueryFormatter

from .models import Person

logger = logging.getLogger(__name__)


class QueryFormatterTests(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.format_sql_calls = []

    def new_format_sql(self, sql):
        # Use time() to introduce some uniqueness.
        formatted = "Formatted! %s at %s" % (sql.upper(), time())
        self.format_sql_calls.append({sql: formatted})
        return formatted

    def make_handler(self, **formatter_kwargs):
        formatter = QueryFormatter(**formatter_kwargs)

        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)

        original_level = logger.getEffectiveLevel()
        logger.setLevel(logging.DEBUG)
        self.addCleanup(logger.setLevel, original_level)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)

        return handler

    def do_log(self, msg, *logger_args, alias=DEFAULT_DB_ALIAS, extra=None):
        if extra is None:
            extra = {}
        if alias and "alias" not in extra:
            extra["alias"] = alias
        # Patch connection's format_debug_sql to ensure it was properly called.
        with mock.patch.object(
            connections[alias].ops, "format_debug_sql", side_effect=self.new_format_sql
        ):
            logger.info(msg, *logger_args, extra=extra)

    def assertLogRecord(self, handler, expected):
        handler.stream.seek(0)
        self.assertEqual(handler.stream.read().strip(), expected)

    def assertSQLFormatted(self, handler, sql, total_calls=1):
        self.assertEqual(len(self.format_sql_calls), total_calls)
        formatted_sql = self.format_sql_calls[0][sql]
        expected = f"=> Executing query duration=3.142 sql={formatted_sql}"
        self.assertLogRecord(handler, expected)

    def test_formats_sql_bracket_format_style(self):
        handler = self.make_handler(
            fmt="{message} duration={duration:.3f} sql={sql}", style="{"
        )
        msg = "=> Executing query"
        sql = "select * from foo"

        self.do_log(msg, extra={"sql": sql, "duration": 3.1416})
        self.assertSQLFormatted(handler, sql)

    def test_formats_sql_named_fmt_format_style(self):
        handler = self.make_handler(
            fmt="%(message)s duration=%(duration).3f sql=%(sql)s"
        )
        msg = "=> Executing query"
        sql = "select * from foo"

        self.do_log(msg, extra={"sql": sql, "duration": 3.1416})
        self.assertSQLFormatted(handler, sql)

    def test_formats_sql_named_percent_format_style(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%(duration).3f sql=%(sql)s"
        sql = "select * from foo"

        self.do_log(msg, {"duration": 3.1416, "sql": sql})
        self.assertSQLFormatted(handler, sql)

    def test_formats_sql_default_percent_format_style(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%.3f sql=%s"
        sql = "select * from foo"

        self.do_log(msg, 3.1416, sql)
        self.assertSQLFormatted(handler, sql)

    def test_formats_sql_multiple_matching_sql(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%.3f sql=%s"
        sql = "select * from foo"

        self.do_log(msg, 3.1416, sql, extra={"duration": 3.1416, "sql": sql})
        self.assertSQLFormatted(handler, sql)

    def test_formats_sql_multiple_non_matching_sql(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%.3f sql=%s"
        sql1 = "select * from foo"
        sql2 = "select * from other"

        self.do_log(msg, 3.1416, sql1, extra={"duration": 3.1416, "sql": sql2})
        self.assertSQLFormatted(handler, sql1, total_calls=2)
        # Second format call is triggered since the sql are different.
        self.assertEqual(list(self.format_sql_calls[1].keys()), [sql2])

    def test_log_record_no_args(self):
        handler = self.make_handler()
        msg = "=> Executing query no args"

        self.do_log(msg)
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, msg)

    def test_log_record_not_enough_args(self):
        handler = self.make_handler()
        msg = "=> Executing query one args %r"
        args = "not formatted"

        self.do_log(msg, args)
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, msg % args)

    def test_log_record_not_key_in_dict_args(self):
        handler = self.make_handler()
        msg = "=> Executing query missing sql key %(foo)r"
        args = {"foo": "bar"}

        self.do_log(msg, args)
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, msg % args)

    def test_log_record_no_alias(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%.3f sql=%s"
        args = (3.1416, "select * from foo")

        self.do_log(msg, *args, extra={"alias": "does not exist"})
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, msg % args)

    def test_log_record_sql_arg_none(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%.3f sql=%s"
        args = (3.1416, None)

        self.do_log(msg, *args)
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, msg % args)

    def test_log_record_sql_key_none(self):
        handler = self.make_handler()
        msg = "=> Executing query duration=%(duration).3f sql=%(sql)s"
        args = {"duration": 3.1416, "sql": None}

        self.do_log(msg, args)
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, msg % args)

    def test_log_record_sql_extra_none(self):
        handler = self.make_handler(
            fmt="{message} duration={duration:.3f} sql={sql}", style="{"
        )
        msg = "=> Executing query"

        self.do_log(msg, extra={"sql": None, "duration": 3.1416})
        self.assertEqual(self.format_sql_calls, [])
        self.assertLogRecord(handler, f"{msg} duration=3.142 sql=None")


@unittest.skipUnless(
    connection.vendor == "sqlite", "Only run on sqlite so we can check output SQL."
)
class TestDebugSQL(unittest.TestCase):
    class PassingTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name="pass").count()

    class FailingTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name="fail").count()
            self.fail()

    class ErrorTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name="error").count()
            raise Exception

    class ErrorSetUpTestDataTest(TestCase):
        @classmethod
        def setUpTestData(cls):
            raise Exception

        def runTest(self):
            pass

    class PassingSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name="subtest-pass").count()

    class FailingSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name="subtest-fail").count()
                self.fail()

    class ErrorSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name="subtest-error").count()
                raise Exception

    def _test_output(self, verbosity):
        runner = DiscoverRunner(debug_sql=True, verbosity=0)
        suite = runner.test_suite()
        suite.addTest(self.FailingTest())
        suite.addTest(self.ErrorTest())
        suite.addTest(self.PassingTest())
        suite.addTest(self.PassingSubTest())
        suite.addTest(self.FailingSubTest())
        suite.addTest(self.ErrorSubTest())
        old_config = runner.setup_databases()
        stream = StringIO()
        resultclass = runner.get_resultclass()
        runner.test_runner(
            verbosity=verbosity,
            stream=stream,
            resultclass=resultclass,
        ).run(suite)
        runner.teardown_databases(old_config)

        return stream.getvalue()

    def test_output_normal(self):
        full_output = self._test_output(1)
        for output in self.expected_outputs:
            self.assertIn(output, full_output)
        for output in self.verbose_expected_outputs:
            self.assertNotIn(output, full_output)

    def test_output_verbose(self):
        full_output = self._test_output(2)
        for output in self.expected_outputs:
            self.assertIn(output, full_output)
        for output in self.verbose_expected_outputs:
            self.assertIn(output, full_output)

    expected_outputs = [
        (
            """SELECT COUNT(*) AS "__count"\n"""
            """FROM "test_runner_person"\n"""
            """WHERE "test_runner_person"."first_name" = 'error'; """
            """args=('error',); alias=default"""
        ),
        (
            """SELECT COUNT(*) AS "__count"\n"""
            """FROM "test_runner_person"\n"""
            """WHERE "test_runner_person"."first_name" = 'fail'; """
            """args=('fail',); alias=default"""
        ),
        (
            """SELECT COUNT(*) AS "__count"\n"""
            """FROM "test_runner_person"\n"""
            """WHERE "test_runner_person"."first_name" = 'subtest-error'; """
            """args=('subtest-error',); alias=default"""
        ),
        (
            """SELECT COUNT(*) AS "__count"\n"""
            """FROM "test_runner_person"\n"""
            """WHERE "test_runner_person"."first_name" = 'subtest-fail'; """
            """args=('subtest-fail',); alias=default"""
        ),
    ]

    test_class_path = "test_runner.test_debug_sql.TestDebugSQL"
    verbose_expected_outputs = [
        f"runTest ({test_class_path}.FailingTest.runTest) ... FAIL",
        f"runTest ({test_class_path}.ErrorTest.runTest) ... ERROR",
        f"runTest ({test_class_path}.PassingTest.runTest) ... ok",
        # If there are errors/failures in subtests but not in test itself,
        # the status is not written. That behavior comes from Python.
        f"runTest ({test_class_path}.FailingSubTest.runTest) ...",
        f"runTest ({test_class_path}.ErrorSubTest.runTest) ...",
        (
            """SELECT COUNT(*) AS "__count"\n"""
            """FROM "test_runner_person"\nWHERE """
            """"test_runner_person"."first_name" = 'pass'; """
            """args=('pass',); alias=default"""
        ),
        (
            """SELECT COUNT(*) AS "__count"\n"""
            """FROM "test_runner_person"\nWHERE """
            """"test_runner_person"."first_name" = 'subtest-pass'; """
            """args=('subtest-pass',); alias=default"""
        ),
    ]

    def test_setupclass_exception(self):
        runner = DiscoverRunner(debug_sql=True, verbosity=0)
        suite = runner.test_suite()
        suite.addTest(self.ErrorSetUpTestDataTest())
        old_config = runner.setup_databases()
        stream = StringIO()
        runner.test_runner(
            verbosity=0,
            stream=stream,
            resultclass=runner.get_resultclass(),
        ).run(suite)
        runner.teardown_databases(old_config)
        output = stream.getvalue()
        self.assertIn(
            "ERROR: setUpClass "
            "(test_runner.test_debug_sql.TestDebugSQL.ErrorSetUpTestDataTest)",
            output,
        )
