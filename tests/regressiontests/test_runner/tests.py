"""
Tests for django test runner
"""
import StringIO

from django.core.exceptions import ImproperlyConfigured
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

class DependencyOrderingTests(unittest.TestCase):

    def test_simple_dependencies(self):
        raw = [
            ('s1', ['alpha']),
            ('s2', ['bravo']),
            ('s3', ['charlie']),
        ]
        dependencies = {
            'alpha': ['charlie'],
            'bravo': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,aliases in ordered]

        self.assertIn('s1', ordered_sigs)
        self.assertIn('s2', ordered_sigs)
        self.assertIn('s3', ordered_sigs)
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s2'))

    def test_chained_dependencies(self):
        raw = [
            ('s1', ['alpha']),
            ('s2', ['bravo']),
            ('s3', ['charlie']),
        ]
        dependencies = {
            'alpha': ['bravo'],
            'bravo': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,aliases in ordered]

        self.assertIn('s1', ordered_sigs)
        self.assertIn('s2', ordered_sigs)
        self.assertIn('s3', ordered_sigs)

        # Explicit dependencies
        self.assertLess(ordered_sigs.index('s2'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s2'))

        # Implied dependencies
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s1'))

    def test_multiple_dependencies(self):
        raw = [
            ('s1', ['alpha']),
            ('s2', ['bravo']),
            ('s3', ['charlie']),
            ('s4', ['delta']),
        ]
        dependencies = {
            'alpha': ['bravo','delta'],
            'bravo': ['charlie'],
            'delta': ['charlie'],
        }

        ordered = simple.dependency_ordered(raw, dependencies=dependencies)
        ordered_sigs = [sig for sig,aliases in ordered]

        self.assertIn('s1', ordered_sigs)
        self.assertIn('s2', ordered_sigs)
        self.assertIn('s3', ordered_sigs)
        self.assertIn('s4', ordered_sigs)

        # Explicit dependencies
        self.assertLess(ordered_sigs.index('s2'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s4'), ordered_sigs.index('s1'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s2'))
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s4'))

        # Implicit dependencies
        self.assertLess(ordered_sigs.index('s3'), ordered_sigs.index('s1'))

    def test_circular_dependencies(self):
        raw = [
            ('s1', ['alpha']),
            ('s2', ['bravo']),
        ]
        dependencies = {
            'bravo': ['alpha'],
            'alpha': ['bravo'],
        }

        self.assertRaises(ImproperlyConfigured, simple.dependency_ordered, raw, dependencies=dependencies)

