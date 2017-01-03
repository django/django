from unittest import skipUnless

from django.db import connection
from django.test import TestCase, mock


class TestDatabaseFeatures(TestCase):

    def test_nonexistent_feature(self):
        self.assertFalse(hasattr(connection.features, 'nonexistent'))


@skipUnless(connection.vendor == 'mysql', 'MySQL backend tests')
class TestMySQLFeatures(TestCase):

    def test_mysql_supports_transactions(self):
        """
        All storage engines except MyISAM support transactions.
        """
        with mock.patch('django.db.connection.features._mysql_storage_engine', 'InnoDB'):
            self.assertTrue(connection.features.supports_transactions)
        del connection.features.supports_transactions
        with mock.patch('django.db.connection.features._mysql_storage_engine', 'MyISAM'):
            self.assertFalse(connection.features.supports_transactions)
        del connection.features.supports_transactions
