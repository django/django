from django.template.defaultfilters import divisibleby
from django.test import SimpleTestCase


class FunctionTests(SimpleTestCase):

    def test_true(self):
        self.assertEqual(divisibleby(4, 2), True)

    def test_false(self):
        self.assertEqual(divisibleby(4, 3), False)
