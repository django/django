from unittest import mock, skipUnless

from django.db import connection
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
