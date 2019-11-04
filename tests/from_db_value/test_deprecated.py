from django.test import TestCase
from django.utils.deprecation import RemovedInDjango30Warning

from .models import Cash, CashModelDeprecated


class FromDBValueDeprecationTests(TestCase):

    def test_deprecation(self):
        msg = (
            'Remove the context parameter from CashFieldDeprecated.from_db_value(). '
            'Support for it will be removed in Django 3.0.'
        )
        CashModelDeprecated.objects.create(cash='12.50')
        with self.assertWarnsMessage(RemovedInDjango30Warning, msg):
            instance = CashModelDeprecated.objects.get()
        self.assertIsInstance(instance.cash, Cash)
