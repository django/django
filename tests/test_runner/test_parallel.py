import unittest

from django.test import SimpleTestCase
from django.test.runner import RemoteTestResult
from django.utils import six

try:
    import tblib
except ImportError:
    tblib = None


class ErrorThatFailsUnpickling(Exception):
    """
    This exception class will fail unpickling both on 2.x and 3.x although with
    slightly different error messages. Both errors relate to incorrect
    arguments passed to __init__.
    """
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2
        super(ErrorThatFailsUnpickling, self).__init__('Message with %s and %s')


class ParallelTestRunnerTest(SimpleTestCase):
    """
    End-to-end tests of the parallel test runner.

    These tests are only meaningful when running tests in parallel using
    the --parallel option, though it doesn't hurt to run them not in
    parallel.
    """

    @unittest.skipUnless(six.PY3, 'subtests were added in Python 3.4')
    def test_subtest(self):
        """
        Check that passing subtests work.
        """
        for i in range(2):
            with self.subTest(index=i):
                self.assertEqual(i, i)


class SampleFailingSubtest(SimpleTestCase):

    # This method name doesn't begin with "test" to prevent test discovery
    # from seeing it.
    def dummy_test(self):
        """
        A dummy test for testing subTest failures.
        """
        for i in range(3):
            with self.subTest(index=i):
                self.assertEqual(i, 1)


class RemoteTestResultTest(SimpleTestCase):

    def test_pickle_errors_detection(self):
        picklable_error = RuntimeError('This is fine')
        not_unpicklable_error = ErrorThatFailsUnpickling('one arg', 'another arg')

        result = RemoteTestResult()
        result._raise_when_not_picklable(picklable_error)

        with self.assertRaisesMessage(TypeError, 'argument'):
            result._raise_when_not_picklable(not_unpicklable_error)

    @unittest.skipUnless(six.PY3 and tblib is not None, 'requires tblib to be installed')
    def test_add_failing_subtests(self):
        """
        Failing subtests are added correctly using addSubTest().
        """
        # Manually run a test with failing subtests to prevent the failures
        # from affecting the actual test run.
        result = RemoteTestResult()
        subtest_test = SampleFailingSubtest(methodName='dummy_test')
        subtest_test.run(result=result)

        events = result.events
        self.assertEqual(len(events), 4)

        event = events[1]
        self.assertEqual(event[0], 'addSubTest')
        self.assertEqual(str(event[2]), 'dummy_test (test_runner.test_parallel.SampleFailingSubtest) (index=0)')
        self.assertEqual(repr(event[3][1]), "AssertionError('0 != 1',)")

        event = events[2]
        self.assertEqual(repr(event[3][1]), "AssertionError('2 != 1',)")
