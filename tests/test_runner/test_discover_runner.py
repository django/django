from contextlib import contextmanager
import os
import sys

from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.utils.unittest import expectedFailure

try:
    import unittest2
except ImportError:
    unittest2 = None


def expectedFailureIf(condition):
    """Marks a test as an expected failure if ``condition`` is met."""
    if condition:
        return expectedFailure
    return lambda func: func


class DiscoverRunnerTest(TestCase):

    def test_dotted_test_module(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample"],
        ).countTestCases()

        self.assertEqual(count, 3)

    def test_dotted_test_class_vanilla_unittest(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestVanillaUnittest"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_class_unittest2(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestUnittest2"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_class_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestDjangoTestCase"],
        ).countTestCases()

        self.assertEqual(count, 1)

    # this test fails if unittest2 is installed from PyPI on Python 2.6
    # refs https://code.djangoproject.com/ticket/20437
    @expectedFailureIf(sys.version_info < (2, 7) and unittest2)
    def test_dotted_test_method_vanilla_unittest(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestVanillaUnittest.test_sample"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_method_unittest2(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestUnittest2.test_sample"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_method_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestDjangoTestCase.test_sample"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_pattern(self):
        count = DiscoverRunner(
            pattern="*_tests.py",
        ).build_suite(["test_discovery_sample"]).countTestCases()

        self.assertEqual(count, 1)

    def test_file_path(self):
        @contextmanager
        def change_cwd_to_tests():
            """Change CWD to tests directory (one level up from this file)"""
            current_dir = os.path.abspath(os.path.dirname(__file__))
            tests_dir = os.path.join(current_dir, '..')
            old_cwd = os.getcwd()
            os.chdir(tests_dir)
            yield
            os.chdir(old_cwd)

        with change_cwd_to_tests():
            count = DiscoverRunner().build_suite(
                ["test_discovery_sample/"],
            ).countTestCases()

        self.assertEqual(count, 4)
