from django.test import TestCase
from django.core import management
from django.db import transaction

from .models import Book


class TestNoInitialDataLoading(TestCase):
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
        self.assertQuerysetEqual(Book.objects.all(), [])

        management.call_command(
            'flush',
            verbosity=0,
            interactive=False,
            load_initial_data=False
        )
        self.assertQuerysetEqual(Book.objects.all(), [])
