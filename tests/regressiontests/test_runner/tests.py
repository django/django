"""
Tests for django test runner
"""
import StringIO

from django.test import simple
from django.utils import unittest

class DjangoTestRunnerTests(unittest.TestCase):

    def test_failfast(self):
        class MockTestOne(unittest.TestCase):
            def runTest(self):
                assert False
        class MockTestTwo(unittest.TestCase):
            def runTest(self):
                assert False

        suite = unittest.TestSuite([MockTestOne(), MockTestTwo()])
        mock_stream = StringIO.StringIO()
        dtr = simple.DjangoTestRunner(verbosity=0, failfast=False, stream=mock_stream)
        result = dtr.run(suite)
        self.assertEqual(2, result.testsRun)
        self.assertEqual(2, len(result.failures))

        dtr = simple.DjangoTestRunner(verbosity=0, failfast=True, stream=mock_stream)
        result = dtr.run(suite)
        self.assertEqual(1, result.testsRun)
        self.assertEqual(1, len(result.failures))
