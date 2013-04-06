from django.db.models import get_app
from django.test.simple import build_suite
from django.utils import unittest


def suite():
    """
    Validate that you can define a custom suite when running tests
    with `django.test.simple.DjangoTestSuiteRunner`.
    """

    testSuite = unittest.TestSuite()
    testSuite.addTest(SuiteOverrideTest('test_suite_override'))
    return testSuite


class SuiteOverrideTest(unittest.TestCase):

    def test_suite_override(self):
        app = get_app("test_client_override")
        suite = build_suite(app)
        self.assertEqual(suite.countTestCases(), 1)


class SampleTests(unittest.TestCase):

    def test_one(self):
        pass

    def test_two(self):
        pass

    def test_threee(self):
        pass
