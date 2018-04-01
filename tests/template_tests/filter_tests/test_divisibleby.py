from django.template.defaultfilters import divisibleby
from django.test import SimpleTestCase


class FunctionTests(SimpleTestCase):

    def test_true(self):
        self.assertIs(divisibleby(4, 2), True)

    def test_false(self):
        self.assertIs(divisibleby(4, 3), False)

    def test_false_fail_silently(self):
        self.assertIs(divisibleby(None, 3), '')