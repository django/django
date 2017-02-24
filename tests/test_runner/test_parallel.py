import unittest

from django.test import SimpleTestCase
from django.test.runner import RemoteTestResult

try:
    import tblib
except ImportError:
    tblib = None


class ExceptionThatFailsUnpickling(Exception):
    """
    After pickling, this class fails unpickling with an error about incorrect
    arguments passed to __init__().
    """
    def __init__(self, arg):
        super().__init__()


class ParallelTestRunnerTest(SimpleTestCase):
    """
    End-to-end tests of the parallel test runner.

    These tests are only meaningful when running tests in parallel using
    the --parallel option, though it doesn't hurt to run them not in
    parallel.
    """

    def test_subtest(self):
        """
        Passing subtests work.
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
        not_unpicklable_error = ExceptionThatFailsUnpickling('arg')

        result = RemoteTestResult()
        result._confirm_picklable(picklable_error)

        msg = '__init__() missing 1 required positional argument'
        with self.assertRaisesMessage(TypeError, msg):
            result._confirm_picklable(not_unpicklable_error)

    @unittest.skipUnless(tblib is not None, 'requires tblib to be installed')
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
