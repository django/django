from unittest import mock, skipUnless

from django.db import connection
from django.db.backends.mysql.features import DatabaseFeatures
from django.test import TestCase


@skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class TestFeatures(TestCase):

    def test_supports_transactions(self):
        """
        All storage engines except MyISAM support transactions.
        """
        with mock.patch('django.db.connection.features._mysql_storage_engine', 'InnoDB'):
            self.assertTrue(connection.features.supports_transactions)
        del connection.features.supports_transactions
        with mock.patch('django.db.connection.features._mysql_storage_engine', 'MyISAM'):
            self.assertFalse(connection.features.supports_transactions)
        del connection.features.supports_transactions

    def test_skip_locked_no_wait(self):
        with mock.MagicMock() as _connection:
            _connection.mysql_version = (8, 0, 1)
            _connection.mysql_is_mariadb = False
            database_features = DatabaseFeatures(_connection)
            self.assertTrue(database_features.has_select_for_update_skip_locked)
            self.assertTrue(database_features.has_select_for_update_nowait)
        with mock.MagicMock() as _connection:
            _connection.mysql_version = (8, 0, 0)
            _connection.mysql_is_mariadb = False
            database_features = DatabaseFeatures(_connection)
            self.assertFalse(database_features.has_select_for_update_skip_locked)
            self.assertFalse(database_features.has_select_for_update_nowait)
