from io import StringIO
from unittest import TestCase, mock, skipIf

from django.core.management.color import supports_color
from django.test.runner import TERMINATOR, DiscoverRunner


@mock.patch.dict('django.core.management.color.os.environ', {'DJANGO_COLORS': ''})
@skipIf(not supports_color(), "terminal does not support color")
class TestColoredRunner(TestCase):

    class PassingTest(TestCase):
        def runTest(self):
            self.assertEqual(1, 1)

    class FailingTest(TestCase):
        def runTest(self):
            self.assertEqual(1, 2)

    class ErrorTest(TestCase):
        def runTest(self):
            raise Exception

    def _test_output(self, verbosity, no_color=True):
        runner = DiscoverRunner(debug_sql=True, verbosity=0, no_color=no_color)
        suite = runner.test_suite()
        suite.addTest(self.FailingTest())
        suite.addTest(self.ErrorTest())
        suite.addTest(self.PassingTest())
        stream = StringIO()
        resultclass = runner.get_resultclass()
        runner.test_runner(
            verbosity=verbosity,
            stream=stream,
            resultclass=resultclass,
            no_color=no_color
        ).run(suite)
        return stream.getvalue()

    def test_no_color_output(self):
        output = self._test_output(1, no_color=True)
        self.assertNotIn(TERMINATOR, output)
        self.assertIn('FE.', output)

    def test_colored_output_error(self):
        output = self._test_output(1, no_color=False)
        self.assertIn('\x1b[35;1mE\x1b[0m', output)
        self.assertIn('\x1b[35;1mERROR: \x1b[37;1mrunTest\x1b[0m', output)

    def test_colored_output_fail(self):
        output = self._test_output(1, no_color=False)
        self.assertIn('\x1b[31;1mF\x1b[0m', output)
        self.assertIn('\x1b[31;1mFAIL: \x1b[37;1mrunTest\x1b[0m', output)

    def test_colored_output_success(self):
        output = self._test_output(1, no_color=False)
        self.assertIn('\x1b[32m.\x1b[0m', output)

    def test_colored_summary(self):
        output = self._test_output(1, no_color=False)
        # tests count
        self.assertIn('Ran \x1b[37;1m3\x1b[0m tests', output)
        # time taken
        self.assertIn('in \x1b[37;1m', output)
        self.assertIn('\x1b[0ms', output)
        # failures count
        self.assertIn('failures=\x1b[31;1m1\x1b[0m', output)
        # errors count
        self.assertIn('errors=\x1b[35;1m1\x1b[0m', output)

    def test_colored_verbose_tests_list(self):
        output = self._test_output(2, no_color=False)
        self.assertIn(
            '\x1b[37;1mrunTest\x1b[0m (test_runner.test_colored_runner.TestColoredRunner.FailingTest)'
            ' ... \x1b[31;1mFAIL\n\x1b[0m', output)
        self.assertIn('\x1b[37;1mrunTest\x1b[0m (test_runner.test_colored_runner.TestColoredRunner.ErrorTest)'
                      ' ... \x1b[35;1mERROR\n\x1b[0m', output)
        self.assertIn('\x1b[37;1mrunTest\x1b[0m (test_runner.test_colored_runner.TestColoredRunner.PassingTest)'
                      ' ... \x1b[32mok\n\x1b[0m', output)
