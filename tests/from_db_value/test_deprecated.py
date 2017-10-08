import warnings

from django.test import TestCase

from .models import Cash, CashModelDeprecated


class FromDBValueDeprecationTests(TestCase):

    def test_deprecation(self):
        CashModelDeprecated.objects.create(cash='12.50')
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            instance = CashModelDeprecated.objects.get()
        self.assertIsInstance(instance.cash, Cash)
        self.assertEqual(len(warns), 1)
        msg = str(warns[0].message)
        self.assertEqual(
            msg,
            'Remove the context parameter from CashFieldDeprecated.from_db_value(). '
            'Support for it will be removed in Django 3.0.'
        )
