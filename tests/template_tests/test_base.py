from django.template.base import Variable, VariableDoesNotExist
from django.test import SimpleTestCase


class VariableDoesNotExistTests(SimpleTestCase):
    def test_str(self):
        exc = VariableDoesNotExist(msg='Failed lookup in %r', params=({'foo': 'bar'},))
        self.assertEqual(str(exc), "Failed lookup in {'foo': 'bar'}")


class VariableTests(SimpleTestCase):
    def test_integer_literals(self):
        self.assertEqual(Variable('999999999999999999999999999').literal, 999999999999999999999999999)
