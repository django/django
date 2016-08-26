import unittest

from django.test import TestCase
from django.test.runner import RemoteTestResult
from django.utils import six

try:
    import tblib
except ImportError:
    tblib = None


class ParallelTestRunnerTest(TestCase):

    """
    End-to-end tests of the parallel test runner.

    These tests are only meaningful when running tests in parallel using
    the --parallel option, though it doesn't hurt to run them not in
    parallel.
    """

    @unittest.skipUnless(six.PY3, "subtests were added in Python 3.4")
    def test_subtest(self):
        """
        Check that passing subtests work.
        """
        for i in range(2):
            with self.subTest(index=i):
                self.assertEqual(i, i)


class SampleFailingSubtest(TestCase):

    # Choose a method name not beginning with "test" to prevent this method
    # from being picked up by test discovery.
    def dummy_test(self):
        """
        A dummy test for testing subTest failures.
        """
        for i in range(3):
            with self.subTest(index=i):
                self.assertEqual(i, 1)


class RemoteTestResultTest(TestCase):

    @unittest.skipUnless(six.PY3 and tblib is not None, "requires tblib to be installed")
    def test_add_failing_subtests(self):
        """
        Test that failing subtests are added correctly using addSubTest().
        """
        # Run a test with failing subtests manually to prevent the failures
        # from affecting the actual test run.
        result = RemoteTestResult()
        subtest_test = SampleFailingSubtest(methodName="dummy_test")
        subtest_test.run(result=result)

        events = result.events
        self.assertEqual(len(events), 4)

        event = events[1]
        self.assertEqual(event[0], "addSubTest")
        self.assertEqual(
            str(event[2]),
            "dummy_test (test_runner.test_parallel.SampleFailingSubtest) (index=0)")
        self.assertEqual(repr(event[3][1]), "AssertionError('0 != 1',)")

        event = events[2]
        self.assertEqual(repr(event[3][1]), "AssertionError('2 != 1',)")
