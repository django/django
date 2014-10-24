from django.test import TestCase, TransactionTestCase
from django.core import management
from django.db import transaction

from .models import Book

class TestNoInitialDataLoading(TransactionTestCase):
    available_apps = ['fixtures_migration']

    def test_migrate(self):
        with transaction.atomic():
            Book.objects.all().delete()

            management.call_command(
                'migrate',
                verbosity=0,
            )
            self.assertQuerysetEqual(Book.objects.all(), [])

    def test_flush(self):
        # Test presence of fixture (flush called by TransactionTestCase)
        self.assertQuerysetEqual(Book.objects.all(), [])

        with transaction.atomic():
            management.call_command(
                'flush',
                verbosity=0,
                interactive=False,
                load_initial_data=False
            )
            self.assertQuerysetEqual(Book.objects.all(), [])
