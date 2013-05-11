from django.test import TestCase
from django.test.runner import DiscoverRunner


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
        count = DiscoverRunner().build_suite(
            ["test_discovery_sample/"],
        ).countTestCases()

        self.assertEqual(count, 4)
