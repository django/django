from django.test import TestCase, TestExtension
from django.test.runner import DiscoverRunner
from django.utils import six

state = {
    'count': 0,
}


class PlainRunner(DiscoverRunner):
    """Strip default test runner behaviour."""
    extensions = []

    def setup_test_environment(self):
        pass

    def setup_databases(self):
        pass

    def teardown_test_environment(self):
        pass

    def teardown_databases(self, config):
        pass


class EnvironmentExtension(TestExtension):
    def setup_environment(self):
        state['count'] += 1

    def teardown_environment(self):
        state['count'] -= 1


class EnvironmentRunner(PlainRunner):
    extensions = ['test_runner.test_extensions.EnvironmentExtension']


class TestCaseExtension(TestExtension):
    def setup_test(self):
        state['count'] += 1

    def teardown_test(self):
        state['count'] -= 1


class TestCaseRunner(PlainRunner):
    extensions = ['test_runner.test_extensions.TestCaseExtension']


class TestExtensions(TestCase):
    def _run_tests(self, runner_class, tests):
        runner = runner_class()
        stream = six.StringIO()
        return runner.run_tests(test_labels=[], extra_tests=tests, stream=stream)

    class CountOneTest(TestCase):
        def runTest(self):
            self.assertEqual(state['count'], 1)

    class ExtendedCountOneTest(TestCase):
        extensions = ['test_runner.test_extensions.EnvironmentExtension']

        def runTest(self):
            self.assertEqual(state['count'], 1)

    class ClassExtendedCountOneTest(TestCase):
        extensions = [EnvironmentExtension]

        def runTest(self):
            self.assertEqual(state['count'], 1)

    class CountTwoTest(TestCase):
        extensions = ['test_runner.test_extensions.TestCaseExtension']

        def runTest(self):
            self.assertEqual(state['count'], 2)

    def test_setup_environment_runner(self):
        result = self._run_tests(EnvironmentRunner, [self.CountOneTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)

    def test_setup_environment_testcase(self):
        result = self._run_tests(PlainRunner, [self.ExtendedCountOneTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)

    def test_setup_environment_testcase_class(self):
        result = self._run_tests(PlainRunner, [self.ClassExtendedCountOneTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)

    def test_setup_test_runner(self):
        result = self._run_tests(TestCaseRunner, [self.CountOneTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)

    def test_multiple_extensions(self):
        result = self._run_tests(EnvironmentRunner, [self.CountTwoTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)

    def test_deduplication(self):
        result = self._run_tests(EnvironmentRunner, [self.ExtendedCountOneTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)

    def test_deduplication_classes(self):
        result = self._run_tests(EnvironmentRunner, [self.ClassExtendedCountOneTest()])
        self.assertEqual(result, 0)
        self.assertEqual(state['count'], 0)
