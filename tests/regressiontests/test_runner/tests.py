"""
Tests for django test runner
"""
import StringIO
import unittest
from django.core.exceptions import ImproperlyConfigured
from django.test import simple

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

class DependencyOrderingTests(unittest.TestCase):

    def test_simple_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
            ('s3', ('s3_db', ['charlie'])),
        ]
        dependencies = {
            'alpha': ['charlie'],
            'bravo': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,value in ordered]

        self.assertTrue('s1' in ordered_sigs)
        self.assertTrue('s2' in ordered_sigs)
        self.assertTrue('s3' in ordered_sigs)
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s1'))
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s2'))

    def test_chained_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
            ('s3', ('s3_db', ['charlie'])),
        ]
        dependencies = {
            'alpha': ['bravo'],
            'bravo': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,value in ordered]

        self.assertTrue('s1' in ordered_sigs)
        self.assertTrue('s2' in ordered_sigs)
        self.assertTrue('s3' in ordered_sigs)

        # Explicit dependencies
        self.assertTrue(ordered_sigs.index('s2') < ordered_sigs.index('s1'))
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s2'))

        # Implied dependencies
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s1'))

    def test_multiple_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
            ('s3', ('s3_db', ['charlie'])),
            ('s4', ('s4_db', ['delta'])),
        ]
        dependencies = {
            'alpha': ['bravo','delta'],
            'bravo': ['charlie'],
            'delta': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,aliases in ordered]

        self.assertTrue('s1' in ordered_sigs)
        self.assertTrue('s2' in ordered_sigs)
        self.assertTrue('s3' in ordered_sigs)
        self.assertTrue('s4' in ordered_sigs)

        # Explicit dependencies
        self.assertTrue(ordered_sigs.index('s2') < ordered_sigs.index('s1'))
        self.assertTrue(ordered_sigs.index('s4') < ordered_sigs.index('s1'))
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s2'))
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s4'))

        # Implicit dependencies
        self.assertTrue(ordered_sigs.index('s3') < ordered_sigs.index('s1'))

    def test_circular_dependencies(self):
        raw = [
            ('s1', ('s1_db', ['alpha'])),
            ('s2', ('s2_db', ['bravo'])),
        ]
        dependencies = {
            'bravo': ['alpha'],
            'alpha': ['bravo'],
        }

        self.assertRaises(ImproperlyConfigured, simple.dependency_ordered, raw, dependencies=dependencies)

