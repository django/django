from unittest import mock, skipUnless

from django.db import connection
from django.db.backends.mysql.features import DatabaseFeatures
from django.test import TestCase


@skipUnless(connection.vendor == "mysql", "MySQL tests")
class TestFeatures(TestCase):
    def test_supports_transactions(self):
        """
        All storage engines except MyISAM support transactions.
        """
        del connection.features.supports_transactions
        with mock.patch(
            "django.db.connection.features._mysql_storage_engine", "InnoDB"
        ):
            self.assertTrue(connection.features.supports_transactions)
        del connection.features.supports_transactions
        with mock.patch(
            "django.db.connection.features._mysql_storage_engine", "MyISAM"
        ):
            self.assertFalse(connection.features.supports_transactions)
        del connection.features.supports_transactions

    def test_allows_auto_pk_0(self):
        with mock.MagicMock() as _connection:
            _connection.sql_mode = {"NO_AUTO_VALUE_ON_ZERO"}
            database_features = DatabaseFeatures(_connection)
            self.assertIs(database_features.allows_auto_pk_0, True)
