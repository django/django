from contextlib import contextmanager
import os
from unittest import TestSuite, TextTestRunner, defaultTestLoader

from django.test import TestCase
from django.test.runner import DiscoverRunner


@contextmanager
def change_cwd(directory):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    new_dir = os.path.join(current_dir, directory)
    old_cwd = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(old_cwd)


class DiscoverRunnerTest(TestCase):

    def test_dotted_test_module(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample"],
        ).countTestCases()

        self.assertEqual(count, 4)

    def test_dotted_test_class_vanilla_unittest(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestVanillaUnittest"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_class_django_testcase(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.TestDjangoTestCase"],
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
        with change_cwd(".."):
            count = DiscoverRunner().build_suite(
                ["test_discovery_sample/"],
            ).countTestCases()

        self.assertEqual(count, 5)

    def test_empty_label(self):
        """
        If the test label is empty, discovery should happen on the current
        working directory.
        """
        with change_cwd("."):
            suite = DiscoverRunner().build_suite([])
            self.assertEqual(
                suite._tests[0].id().split(".")[0],
                os.path.basename(os.getcwd()),
            )

    def test_empty_test_case(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.EmptyTestCase"],
        ).countTestCases()

        self.assertEqual(count, 0)

    def test_discovery_on_package(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_ignore_adjacent(self):
        """
        When given a dotted path to a module, unittest discovery searches
        not just the module, but also the directory containing the module.

        This results in tests from adjacent modules being run when they
        should not. The discover runner avoids this behavior.
        """
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.empty"],
        ).countTestCases()

        self.assertEqual(count, 0)

    def test_testcase_ordering(self):
        with change_cwd(".."):
            suite = DiscoverRunner().build_suite(["test_discovery_sample/"])
            self.assertEqual(
                suite._tests[0].__class__.__name__,
                'TestDjangoTestCase',
                msg="TestDjangoTestCase should be the first test case")
            self.assertEqual(
                suite._tests[1].__class__.__name__,
                'TestZimpleTestCase',
                msg="TestZimpleTestCase should be the second test case")
            # All others can follow in unspecified order, including doctests
            self.assertIn('DocTestCase', [t.__class__.__name__ for t in suite._tests[2:]])

    def test_overrideable_test_suite(self):
        self.assertEqual(DiscoverRunner().test_suite, TestSuite)

    def test_overrideable_test_runner(self):
        self.assertEqual(DiscoverRunner().test_runner, TextTestRunner)

    def test_overrideable_test_loader(self):
        self.assertEqual(DiscoverRunner().test_loader, defaultTestLoader)
