from django.test import TransactionTestCase
from .models import Book


class MigrationDataPersistenceTestCase(TransactionTestCase):
    """
    Tests that data loaded in migrations is available if we set
    serialized_rollback = True.
    """

    available_apps = ["migration_test_data_persistence"]
    serialized_rollback = True

    def test_persistence(self):
        self.assertEqual(
            Book.objects.count(),
            1,
        )


class MigrationDataNoPersistenceTestCase(TransactionTestCase):
    """
    Tests the failure case
    """

    available_apps = ["migration_test_data_persistence"]
    serialized_rollback = False

    def test_no_persistence(self):
        self.assertEqual(
            Book.objects.count(),
            0,
        )
