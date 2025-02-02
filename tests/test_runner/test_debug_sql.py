import unittest
from io import StringIO

from django.db import connection
from django.test import TestCase
from django.test.runner import DiscoverRunner

from .models import Person


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
