from django.core import management
from django.test import TestCase
from django.test.utils import override_system_checks

from .models import Book


class TestNoInitialDataLoading(TestCase):
    """
    Apps with migrations should ignore initial data. This test can be removed
    in Django 1.9 when migrations become required and initial data is no longer
    supported.
    """
    available_apps = ['fixtures_migration']

    @override_system_checks([])
    def test_migrate(self):
        self.assertQuerysetEqual(Book.objects.all(), [])
        management.call_command(
            'migrate',
            verbosity=0,
        )
        self.assertQuerysetEqual(Book.objects.all(), [])

    @override_system_checks([])
    def test_flush(self):
        self.assertQuerysetEqual(Book.objects.all(), [])
        management.call_command(
            'flush',
            verbosity=0,
            interactive=False,
            load_initial_data=False
        )
        self.assertQuerysetEqual(Book.objects.all(), [])
