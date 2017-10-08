from decimal import Decimal

from django.template.defaultfilters import pluralize
from django.test import SimpleTestCase


class FunctionTests(SimpleTestCase):

    def test_integers(self):
        self.assertEqual(pluralize(1), '')
        self.assertEqual(pluralize(0), 's')
        self.assertEqual(pluralize(2), 's')

    def test_floats(self):
        self.assertEqual(pluralize(0.5), 's')
        self.assertEqual(pluralize(1.5), 's')

    def test_decimals(self):
        self.assertEqual(pluralize(Decimal(1)), '')
        self.assertEqual(pluralize(Decimal(0)), 's')
        self.assertEqual(pluralize(Decimal(2)), 's')

    def test_lists(self):
        self.assertEqual(pluralize([1]), '')
        self.assertEqual(pluralize([]), 's')
        self.assertEqual(pluralize([1, 2, 3]), 's')

    def test_suffixes(self):
        self.assertEqual(pluralize(1, 'es'), '')
        self.assertEqual(pluralize(0, 'es'), 'es')
        self.assertEqual(pluralize(2, 'es'), 'es')
        self.assertEqual(pluralize(1, 'y,ies'), 'y')
        self.assertEqual(pluralize(0, 'y,ies'), 'ies')
        self.assertEqual(pluralize(2, 'y,ies'), 'ies')
        self.assertEqual(pluralize(0, 'y,ies,error'), '')

    def test_no_len_type(self):
        self.assertEqual(pluralize(object(), 'y,es'), 'y')
        self.assertEqual(pluralize(object(), 'es'), '')

    def test_value_error(self):
        self.assertEqual(pluralize('', 'y,es'), 'y')
