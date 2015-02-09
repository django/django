from django.test import TestCase, TransactionTestCase

from .models import Book


class MigrationDataPersistenceTestCase(TransactionTestCase):
    """
    Tests that data loaded in migrations is available if we set
    serialized_rollback = True on TransactionTestCase
    """

    available_apps = ["migration_test_data_persistence"]
    serialized_rollback = True

    def test_persistence(self):
        self.assertEqual(
            Book.objects.count(),
            1,
        )


class MigrationDataNormalPersistenceTestCase(TestCase):
    """
    Tests that data loaded in migrations is available on TestCase
    """

    def test_persistence(self):
        self.assertEqual(
            Book.objects.count(),
            1,
        )
