import json
from unittest import mock

from django.apps import apps
from django.db import connections
from django.test import TestCase, TransactionTestCase, override_settings

from .models import Car


class TestSerializedContentMockMixin:
    """
    Use this mixin on each test involving TransactionTestCase and
    serialized_rollback = True option to avoid test dependencies. It mocks what
    would be serialized after initial data migrations and restores it at the
    end of the test.
    """
    initial_data_migration = '[]'
    _connections_test_serialized_content = {}

    def _pre_setup(self):
        for db_name in self._databases_names(include_mirrors=False):
            self._connections_test_serialized_content[db_name] = connections[db_name]._test_serialized_contents
            connections[db_name]._test_serialized_contents = self.initial_data_migration
        super()._pre_setup()

    def _post_teardown(self):
        super()._post_teardown()
        for db_name in self._databases_names(include_mirrors=False):
            connections[db_name]._test_serialized_contents = self._connections_test_serialized_content[db_name]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Clean up any data that has been created by the class.
        for data in json.loads(cls.initial_data_migration):
            model = apps.get_model(*data['model'].split('.'))
            model.objects.filter(pk=data['pk']).delete()


class TestSerializedRollbackInhibitsPostMigrate(TestSerializedContentMockMixin, TransactionTestCase):
    """
    TransactionTestCase._fixture_teardown() inhibits the post_migrate signal
    for test classes with serialized_rollback=True.
    """
    available_apps = ['test_utils']
    serialized_rollback = True

    def setUp(self):
        # self.available_apps must be None to test the serialized_rollback
        # condition.
        self.available_apps = None

    def tearDown(self):
        self.available_apps = ['test_utils']

    @mock.patch('django.test.testcases.call_command')
    def test(self, call_command):
        # with a mocked call_command(), this doesn't have any effect.
        self._fixture_teardown()
        call_command.assert_called_with(
            'flush', interactive=False, allow_cascade=False,
            reset_sequences=False, inhibit_post_migrate=True,
            database='default', verbosity=0,
        )


@override_settings(DEBUG=True)  # Enable query logging for test_queries_cleared
class TransactionTestCaseMultiDbTests(TestCase):
    available_apps = []
    multi_db = True

    def test_queries_cleared(self):
        """
        TransactionTestCase._pre_setup() clears the connections' queries_log
        so that it's less likely to overflow. An overflow causes
        assertNumQueries() to fail.
        """
        for alias in connections:
            self.assertEqual(len(connections[alias].queries_log), 0, 'Failed for alias %s' % alias)


class TestDataRestoredOnTearDownIfSerializedRollback(TestSerializedContentMockMixin, TransactionTestCase):
    """
    Initial data is recreated in TransactionTestCase._fixture_teardown()
    after the database is flushed so it's available in next test.
    """
    available_apps = ['test_utils']
    _next_serialized_rollback = True
    initial_data_migration = '[{"model": "test_utils.car", "pk": 666, "fields": {"name": "K 2000"}}]'

    def _post_teardown(self):
        super()._post_teardown()
        # Won't be True if running the tests with --reverse.
        if self._next_serialized_rollback:
            self.assertTrue(Car.objects.exists())

    def test(self):
        pass  # Should be the only one in this class.


class TestDataNotRestoredOnTearDownIfNotSerializedRollback(TestSerializedContentMockMixin, TransactionTestCase):
    """
    Initial data isn't recreated in TransactionTestCase._fixture_teardown()
    if _next_serialized_rollback is False.
    """
    available_apps = ['test_utils']
    _next_serialized_rollback = False
    initial_data_migration = '[{"model": "test_utils.car", "pk": 666, "fields": {"name": "K 2000"}}]'

    def _post_teardown(self):
        super()._post_teardown()
        self.assertFalse(Car.objects.exists())

    def test(self):
        pass  # Should be the only one in this class.
