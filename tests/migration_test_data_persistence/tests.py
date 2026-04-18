from django.core.management import call_command
from django.test import TestCase, TransactionTestCase

from .models import Book


class MigrationDataPersistenceTestCase(TransactionTestCase):
    """
    Data loaded in migrations is available if
    TransactionTestCase.serialized_rollback = True.
    """

    available_apps = ["migration_test_data_persistence"]
    serialized_rollback = True

    def test_persistence(self):
        self.assertEqual(
            Book.objects.count(),
            1,
        )


class MigrationDataPersistenceClassSetup(TransactionTestCase):
    """
    Data loaded in migrations is available during class setup if
    TransactionTestCase.serialized_rollback = True.
    """

    available_apps = ["migration_test_data_persistence"]
    serialized_rollback = True

    @classmethod
    def setUpClass(cls):
        # Simulate another TransactionTestCase having just torn down.
        call_command("flush", verbosity=0, interactive=False, allow_cascade=True)
        super().setUpClass()
        cls.book = Book.objects.first()

    def test_data_available_in_class_setup(self):
        self.assertIsInstance(self.book, Book)


class MigrationDataNormalPersistenceTestCase(TestCase):
    """
    Data loaded in migrations is available on TestCase
    """

    def test_persistence(self):
        self.assertEqual(
            Book.objects.count(),
            1,
        )
