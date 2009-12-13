"""
Tests for django test runner
"""
import StringIO
import unittest
import django
from django.test import TestCase, TransactionTestCase, simple 

class DjangoTestRunnerTests(TestCase):
    
    def test_failfast(self):
        class MockTestOne(TransactionTestCase):
            def runTest(self):
                assert False
        class MockTestTwo(TransactionTestCase):
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
