from os.path import dirname, join, realpath

from django.test import TestCase
from django.test.runner import DiscoverRunner


class DiscoverRunnerTest(TestCase):

    def test_single_app_with_discovery(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample"],
        ).countTestCases()

        self.assertEqual(count, 4)

    def test_multiple_apps_with_discovery(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample", "test_discovery_sample2"],
        ).countTestCases()

        self.assertEqual(count, 5)

    def test_dotted_test_module(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample"],
        ).countTestCases()

        self.assertEqual(count, 3)

    def test_dotted_test_class(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.Test1"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_dotted_test_method(self):
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample.tests_sample.Test1.test_sample"],
        ).countTestCases()

        self.assertEqual(count, 1)

    def test_mixed(self):
        count = DiscoverRunner().build_suite([
            "test_discovery_sample.tests_sample.Test1.test_sample",
            "test_discovery_sample2",
        ]).countTestCases()

        self.assertEqual(count, 2)

    def test_pattern(self):
        root = realpath(join(dirname(__file__), "../test_discovery_sample"))

        count = DiscoverRunner(
            pattern="*_tests.py",
            root=root,
        ).build_suite().countTestCases()

        self.assertEqual(count, 1)

    def test_root(self):
        root = realpath(join(dirname(__file__), "../test_discovery_sample2"))

        count = DiscoverRunner(
            root=root,
        ).build_suite().countTestCases()

        self.assertEqual(count, 1)

    def test_top(self):
        top = realpath(join(dirname(__file__), ".."))
        root = realpath(join(top, "test_discovery_sample2"))

        count = DiscoverRunner(
            root=root,
            top_level=top,
        ).build_suite().countTestCases()

        self.assertEqual(count, 1)

    def test_installed(self):
        count = DiscoverRunner(
            installed=True,
        ).build_suite().countTestCases()

        self.assertTrue(count > 50)
