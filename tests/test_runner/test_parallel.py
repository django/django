import os
import pickle
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock
from unittest.case import TestCase
from unittest.result import TestResult
from unittest.suite import TestSuite, _ErrorHolder

from django.test import SimpleTestCase
from django.test.runner import (
    ParallelTestSuite,
    RemoteTestResult,
    _wait_for_worker_results,
)

from . import models

try:
    import tblib.pickling_support
except ImportError:
    tblib = None


def _test_error_exc_info():
    try:
        raise ValueError("woops")
    except ValueError:
        return sys.exc_info()


class ExceptionThatFailsUnpickling(Exception):
    """
    After pickling, this class fails unpickling with an error about incorrect
    arguments passed to __init__().
    """

    def __init__(self, arg):
        super().__init__()

    def __reduce__(self):
        # tblib 3.2+ makes exception subclasses picklable by default.
        # Return (cls, ()) so the constructor fails on unpickle, preserving
        # the needed behavior for test_pickle_errors_detection.
        return (self.__class__, ())


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

    def test_system_checks(self):
        self.assertEqual(models.Person.system_check_run_count, 1)


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

    # This method name doesn't begin with "test" to prevent test discovery
    # from seeing it.
    def pickle_error_test(self):
        with self.subTest("TypeError: cannot pickle memoryview object"):
            self.x = memoryview(b"")
            self.fail("expected failure")


class SampleErrorTest(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        raise ValueError("woops")
        super().setUpClass()

    # This method name doesn't begin with "test" to prevent test discovery
    # from seeing it.
    def dummy_test(self):
        raise AssertionError("SampleErrorTest.dummy_test() was called")


class RemoteTestResultTest(SimpleTestCase):
    def test_was_successful_no_events(self):
        result = RemoteTestResult()
        self.assertIs(result.wasSuccessful(), True)

    def test_was_successful_one_success(self):
        result = RemoteTestResult()
        test = None
        result.startTest(test)
        try:
            result.addSuccess(test)
        finally:
            result.stopTest(test)
        self.assertIs(result.wasSuccessful(), True)

    def test_was_successful_one_expected_failure(self):
        result = RemoteTestResult()
        test = None
        result.startTest(test)
        try:
            result.addExpectedFailure(test, _test_error_exc_info())
        finally:
            result.stopTest(test)
        self.assertIs(result.wasSuccessful(), True)

    def test_was_successful_one_skip(self):
        result = RemoteTestResult()
        test = None
        result.startTest(test)
        try:
            result.addSkip(test, "Skipped")
        finally:
            result.stopTest(test)
        self.assertIs(result.wasSuccessful(), True)

    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_was_successful_one_error(self):
        result = RemoteTestResult()
        test = None
        result.startTest(test)
        try:
            result.addError(test, _test_error_exc_info())
        finally:
            result.stopTest(test)
        self.assertIs(result.wasSuccessful(), False)

    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_was_successful_one_failure(self):
        result = RemoteTestResult()
        test = None
        result.startTest(test)
        try:
            result.addFailure(test, _test_error_exc_info())
        finally:
            result.stopTest(test)
        self.assertIs(result.wasSuccessful(), False)

    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_add_error_before_first_test(self):
        result = RemoteTestResult()
        test_id = "test_foo (tests.test_foo.FooTest.test_foo)"
        test = _ErrorHolder(test_id)
        # Call addError() without a call to startTest().
        result.addError(test, _test_error_exc_info())

        (event,) = result.events
        self.assertEqual(event[0], "addError")
        self.assertEqual(event[1], -1)
        self.assertEqual(event[2], test_id)
        error_type, _, _ = event[3]
        self.assertEqual(error_type, ValueError)
        self.assertIs(result.wasSuccessful(), False)

    def test_picklable(self):
        result = RemoteTestResult()
        loaded_result = pickle.loads(pickle.dumps(result))
        self.assertEqual(result.events, loaded_result.events)

    def test_pickle_errors_detection(self):
        picklable_error = RuntimeError("This is fine")
        not_unpicklable_error = ExceptionThatFailsUnpickling("arg")

        result = RemoteTestResult()
        result._confirm_picklable(picklable_error)

        # The exception can be pickled but not unpickled.
        pickle.dumps(not_unpicklable_error)
        msg = "__init__() missing 1 required positional argument"
        with self.assertRaisesMessage(TypeError, msg):
            result._confirm_picklable(not_unpicklable_error)

    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_unpicklable_subtest(self):
        result = RemoteTestResult()
        subtest_test = SampleFailingSubtest(methodName="pickle_error_test")
        subtest_test.run(result=result)

        events = result.events
        subtest_event = events[1]
        assertion_error = subtest_event[3]
        self.assertEqual(str(assertion_error[1]), "expected failure")

    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_add_failing_subtests(self):
        """
        Failing subtests are added correctly using addSubTest().
        """
        # Manually run a test with failing subtests to prevent the failures
        # from affecting the actual test run.
        result = RemoteTestResult()
        subtest_test = SampleFailingSubtest(methodName="dummy_test")
        subtest_test.run(result=result)

        events = result.events
        self.assertEqual(len(events), 5)
        self.assertIs(result.wasSuccessful(), False)

        event = events[1]
        self.assertEqual(event[0], "addSubTest")
        self.assertEqual(
            str(event[2]),
            "dummy_test (test_runner.test_parallel.SampleFailingSubtest.dummy_test) "
            "(index=0)",
        )
        self.assertEqual(repr(event[3][1]), "AssertionError('0 != 1')")

        event = events[2]
        self.assertEqual(repr(event[3][1]), "AssertionError('2 != 1')")

    def test_add_duration(self):
        result = RemoteTestResult()
        result.addDuration(None, 2.3)
        self.assertEqual(result.collectedDurations, [("None", 2.3)])


class ParallelTestSuiteTest(SimpleTestCase):
    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_handle_add_error_before_first_test(self):
        dummy_subsuites = []
        pts = ParallelTestSuite(dummy_subsuites, processes=2)
        result = TestResult()
        remote_result = RemoteTestResult()
        test = SampleErrorTest(methodName="dummy_test")
        suite = TestSuite([test])
        suite.run(remote_result)
        for event in remote_result.events:
            pts.handle_event(result, tests=list(suite), event=event)

        self.assertEqual(len(result.errors), 1)
        actual_test, tb_and_details_str = result.errors[0]
        self.assertIsInstance(actual_test, _ErrorHolder)
        self.assertEqual(
            actual_test.id(), "setUpClass (test_runner.test_parallel.SampleErrorTest)"
        )
        self.assertIn("Traceback (most recent call last):", tb_and_details_str)
        self.assertIn("ValueError: woops", tb_and_details_str)

    def test_handle_add_error_during_test(self):
        dummy_subsuites = []
        pts = ParallelTestSuite(dummy_subsuites, processes=2)
        result = TestResult()
        test = TestCase()
        err = _test_error_exc_info()
        event = ("addError", 0, err)
        pts.handle_event(result, tests=[test], event=event)

        self.assertEqual(len(result.errors), 1)
        actual_test, tb_and_details_str = result.errors[0]
        self.assertIsInstance(actual_test, TestCase)
        self.assertEqual(actual_test.id(), "unittest.case.TestCase.runTest")
        self.assertIn("Traceback (most recent call last):", tb_and_details_str)
        self.assertIn("ValueError: woops", tb_and_details_str)

    def test_handle_add_failure(self):
        dummy_subsuites = []
        pts = ParallelTestSuite(dummy_subsuites, processes=2)
        result = TestResult()
        test = TestCase()
        err = _test_error_exc_info()
        event = ("addFailure", 0, err)
        pts.handle_event(result, tests=[test], event=event)

        self.assertEqual(len(result.failures), 1)
        actual_test, tb_and_details_str = result.failures[0]
        self.assertIsInstance(actual_test, TestCase)
        self.assertEqual(actual_test.id(), "unittest.case.TestCase.runTest")
        self.assertIn("Traceback (most recent call last):", tb_and_details_str)
        self.assertIn("ValueError: woops", tb_and_details_str)

    def test_handle_add_success(self):
        dummy_subsuites = []
        pts = ParallelTestSuite(dummy_subsuites, processes=2)
        result = TestResult()
        test = TestCase()
        event = ("addSuccess", 0)
        pts.handle_event(result, tests=[test], event=event)

        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)

    @unittest.skipUnless(tblib is not None, "requires tblib to be installed")
    def test_buffer_mode_reports_setupclass_failure(self):
        test = SampleErrorTest("dummy_test")
        remote_result = RemoteTestResult()
        suite = TestSuite([test])
        suite.run(remote_result)

        pts = ParallelTestSuite([suite], processes=2, buffer=True)
        pts.serialized_aliases = set()
        test_result = TestResult()
        test_result.buffer = True

        with (
            mock.patch("multiprocessing.Pipe") as pipe,
            mock.patch("multiprocessing.Process") as process,
            mock.patch("django.test.runner.wait") as wait,
        ):
            parent, child = mock.Mock(), mock.MagicMock()
            pipe.return_value = parent, child
            process.return_value.exitcode = None
            wait.return_value = [parent]
            parent.recv_bytes.side_effect = [
                pickle.dumps(None),
                pickle.dumps((True, (0, remote_result.events))),
            ]
            pts.run(test_result)

        self.assertIn("ValueError: woops", test_result.errors[0][1])

    def run_worker_scenario(self, function, *args):
        # Start outside the test runner's worker, which cannot start children.
        code = (
            "import django; django.setup(); "
            "from test_runner import parallel_worker_cases as cases; "
            f"cases.{function}(*{args!r})"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            cwd=Path(__file__).resolve().parents[1],
            env={**os.environ, "DJANGO_SETTINGS_MODULE": "test_sqlite"},
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_worker_exit_reports_only_interrupted_subsuite(self):
        for method in ("exit_during_test", "exit_on_decode"):
            with self.subTest(method=method):
                self.run_worker_scenario("run_worker_exit_scenario", method)

    @unittest.skipIf(sys.platform == "win32", "Requires POSIX signal delivery.")
    def test_interrupt_stops_waiting_for_worker(self):
        self.run_worker_scenario("run_interrupt_scenario")

    def test_worker_result_encoding_error(self):
        self.run_worker_scenario("run_encoding_error_scenario")

    def test_worker_waits_respect_handle_limit(self):
        connections = list(range(65))
        with mock.patch("django.test.runner.wait", side_effect=[[1], [64]]) as wait:
            self.assertEqual(_wait_for_worker_results(connections), {1, 64})
        self.assertEqual(
            wait.call_args_list,
            [
                mock.call(connections[:60], timeout=0.1),
                mock.call(connections[60:], timeout=0),
            ],
        )
