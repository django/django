from django.test import TestCase
from django.test.runner import DiscoverRunner


class DiscoverRunnerTest(TestCase):

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

    def test_pattern(self):
        count = DiscoverRunner(
            pattern="*_tests.py",
        ).build_suite(["test_discovery_sample"]).countTestCases()

        self.assertEqual(count, 1)
