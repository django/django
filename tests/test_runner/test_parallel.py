import unittest

from django.test import SimpleTestCase
from django.test.runner import RemoteTestResult, TestCaseDTO
from django.utils.version import PY37

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

    def pickle_error_test(self):
        """
        A dummy test for testing TestCaseDTO.
        """
        with self.subTest("I should fail"):
            self.not_pickleable = lambda: 0
            self.assertTrue(False)


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
        trailing_comma = '' if PY37 else ','
        self.assertEqual(repr(event[3][1]), "AssertionError('0 != 1'%s)" % trailing_comma)

        event = events[2]
        self.assertEqual(repr(event[3][1]), "AssertionError('2 != 1'%s)" % trailing_comma)

    @unittest.skipUnless(tblib is not None, 'requires tblib to be installed')
    def test_add_failed_subtest_with_unpickleable_members(self):
        """
        When a SubTest fails in a parallel context and the TestCase contains
        some unpickleable members, we should still be able to send the SubTest
        back to the TestRunner.
        """
        result = RemoteTestResult()
        subtest_test = SampleFailingSubtest(methodName="pickle_error_test")

        # This is the meat of the test: without TestCaseDTO, we'd expect an
        # ugly "Can't pickle local object" exception when trying to run.
        result = subtest_test.run(result=result)

        add_subtest_event = result.events[1]
        error = add_subtest_event[3][1]
        self.assertEqual(str(error), "False is not true")


class TestCaseDTOTest(SimpleTestCase):
    def test_fields_are_set(self):
        """
        TestCaseDTO picks up the right fields from the wrapped TestCase.
        """

        result = RemoteTestResult()
        subtest_test = SampleFailingSubtest(methodName="pickle_error_test")
        result = subtest_test.run(result=result)

        add_subtest_event = result.events[1]
        subtest = add_subtest_event[2]

        self.assertIsInstance(subtest, TestCaseDTO)
        self.assertEqual(subtest.shortDescription(), "A dummy test for testing TestCaseDTO.")
        self.assertEqual(subtest._subDescription(), "[I should fail]")
        self.assertEqual(
            subtest.id(),
            "test_runner.test_parallel.SampleFailingSubtest.pickle_error_test [I should fail]"
        )
        self.assertEqual(
            str(subtest),
            "pickle_error_test (test_runner.test_parallel.SampleFailingSubtest) [I should fail]"
        )
        self.assertEqual(
            subtest.test_case.id(),
            'test_runner.test_parallel.SampleFailingSubtest.pickle_error_test'
        )
