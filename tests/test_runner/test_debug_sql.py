import unittest
from io import StringIO

from django.core.management.color import supports_color
from django.db import connection
from django.test import TestCase
from django.test.runner import DiscoverRunner

from .models import Person


def is_pygments():
    try:
        import pygments  # noqa
    except ImportError:
        return False
    return True


@unittest.mock.patch.dict('django.core.management.color.os.environ', {'DJANGO_COLORS': ''})
@unittest.skipUnless(connection.vendor == 'sqlite', 'Only run on sqlite so we can check output SQL.')
class TestDebugSQL(unittest.TestCase):

    class PassingTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name='pass').count()

    class FailingTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name='fail').count()
            self.fail()

    class ErrorTest(TestCase):
        def runTest(self):
            Person.objects.filter(first_name='error').count()
            raise Exception

    class PassingSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name='subtest-pass').count()

    class FailingSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name='subtest-fail').count()
                self.fail()

    class ErrorSubTest(TestCase):
        def runTest(self):
            with self.subTest():
                Person.objects.filter(first_name='subtest-error').count()
                raise Exception

    def _test_output(self, verbosity, no_color=True):
        runner = DiscoverRunner(debug_sql=True, verbosity=0, no_color=no_color)
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
            no_color=no_color
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

    @unittest.skipUnless(supports_color(), "terminal does not support color")
    @unittest.skipIf(is_pygments(), "pygments is available")
    def test_colored_output(self):
        def mock_sql_highlighter(sql):
            return sql
        full_output = self._test_output(1, no_color=False)
        for output in self.expected_outputs:
            self.assertIn(output, full_output)

    @unittest.skipUnless(supports_color(), "terminal does not support color")
    @unittest.skipIf(is_pygments(), "pygments is available")
    def test_colored_output_verbose(self):
        full_output = self._test_output(2, no_color=False)
        for output in self.expected_outputs:
            self.assertIn(output, full_output)
        for output in self.colored_verbose_expected_outputs:
            self.assertIn(output.decode(), full_output)

    expected_outputs = [
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'error';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'fail';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'subtest-error';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'subtest-fail';'''),
    ]

    verbose_expected_outputs = [
        'runTest (test_runner.test_debug_sql.TestDebugSQL.FailingTest) ... FAIL',
        'runTest (test_runner.test_debug_sql.TestDebugSQL.ErrorTest) ... ERROR',
        'runTest (test_runner.test_debug_sql.TestDebugSQL.PassingTest) ... ok',
        # If there are errors/failures in subtests but not in test itself,
        # the status is not written. That behavior comes from Python.
        'runTest (test_runner.test_debug_sql.TestDebugSQL.FailingSubTest) ...',
        'runTest (test_runner.test_debug_sql.TestDebugSQL.ErrorSubTest) ...',
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'pass';'''),
        ('''SELECT COUNT(*) AS "__count" '''
            '''FROM "test_runner_person" WHERE '''
            '''"test_runner_person"."first_name" = 'subtest-pass';'''),
    ]

    colored_verbose_expected_outputs = [
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.FailingTest) ... \x1b[31;1mFAIL\n\x1b[0m',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.ErrorTest) ... \x1b[35;1mERROR\n\x1b[0m',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.PassingTest) ... \x1b[32mok\n\x1b[0m',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.PassingSubTest) ... \x1b[32mok\n\x1b[0m',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.FailingSubTest) ...',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.ErrorSubTest) (<subtest>)\n\x1b[0m',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.FailingTest)\n\x1b[0m',
        b'\x1b[37;1mrunTest\x1b[0m (test_runner.test_debug_sql.TestDebugSQL.FailingSubTest) (<subtest>)\n\x1b[0m',
    ]
