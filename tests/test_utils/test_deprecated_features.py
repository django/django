from django.db import connections
from django.db.utils import DEFAULT_DB_ALIAS
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils.deprecation import RemovedInDjango31Warning


class AllowDatabaseQueriesDeprecationTests(SimpleTestCase):
    def test_enabled(self):
        class AllowedDatabaseQueries(SimpleTestCase):
            allow_database_queries = True
        message = (
            '`SimpleTestCase.allow_database_queries` is deprecated. Restrict '
            'the databases available during the execution of '
            'test_utils.test_deprecated_features.AllowDatabaseQueriesDeprecationTests.'
            'test_enabled.<locals>.AllowedDatabaseQueries with the '
            '`databases` attribute instead.'
        )
        with self.assertWarnsMessage(RemovedInDjango31Warning, message):
            self.assertEqual(AllowedDatabaseQueries.databases, {'default'})

    def test_explicitly_disabled(self):
        class AllowedDatabaseQueries(SimpleTestCase):
            allow_database_queries = False
        message = (
            '`SimpleTestCase.allow_database_queries` is deprecated. Restrict '
            'the databases available during the execution of '
            'test_utils.test_deprecated_features.AllowDatabaseQueriesDeprecationTests.'
            'test_explicitly_disabled.<locals>.AllowedDatabaseQueries with '
            'the `databases` attribute instead.'
        )
        with self.assertWarnsMessage(RemovedInDjango31Warning, message):
            self.assertEqual(AllowedDatabaseQueries.databases, set())


class MultiDbDeprecationTests(SimpleTestCase):
    def test_transaction_test_case(self):
        class MultiDbTestCase(TransactionTestCase):
            multi_db = True
        message = (
            '`TransactionTestCase.multi_db` is deprecated. Databases '
            'available during this test can be defined using '
            'test_utils.test_deprecated_features.MultiDbDeprecationTests.'
            'test_transaction_test_case.<locals>.MultiDbTestCase.databases.'
        )
        with self.assertWarnsMessage(RemovedInDjango31Warning, message):
            self.assertEqual(MultiDbTestCase.databases, set(connections))
        MultiDbTestCase.multi_db = False
        with self.assertWarnsMessage(RemovedInDjango31Warning, message):
            self.assertEqual(MultiDbTestCase.databases, {DEFAULT_DB_ALIAS})

    def test_test_case(self):
        class MultiDbTestCase(TestCase):
            multi_db = True
        message = (
            '`TestCase.multi_db` is deprecated. Databases available during '
            'this test can be defined using '
            'test_utils.test_deprecated_features.MultiDbDeprecationTests.'
            'test_test_case.<locals>.MultiDbTestCase.databases.'
        )
        with self.assertWarnsMessage(RemovedInDjango31Warning, message):
            self.assertEqual(MultiDbTestCase.databases, set(connections))
        MultiDbTestCase.multi_db = False
        with self.assertWarnsMessage(RemovedInDjango31Warning, message):
            self.assertEqual(MultiDbTestCase.databases, {DEFAULT_DB_ALIAS})
