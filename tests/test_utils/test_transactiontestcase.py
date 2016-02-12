import json

from django.apps import apps
from django.db import connections
from django.test import TransactionTestCase, mock

from .models import Car


class TestSerializedContentMockMixin(object):
    """
    This mixin should be used every time we want to test something involving
    TransactionTestCase and serialized_rollback = True option to avoid test dependencies.
    We mock what would be serialized by Django after initial data migrations, and restore it
    at the end of the test.
    """
    initial_data_migration = '[]'
    _connections_test_serialized_content = {}

    def _pre_setup(self):
        for db_name in self._databases_names(include_mirrors=False):
            self._connections_test_serialized_content[db_name] = connections[db_name]._test_serialized_contents
            connections[db_name]._test_serialized_contents = self.initial_data_migration
        super(TestSerializedContentMockMixin, self)._pre_setup()

    def _post_teardown(self):
        super(TestSerializedContentMockMixin, self)._post_teardown()
        for db_name in self._databases_names(include_mirrors=False):
            connections[db_name]._test_serialized_contents = self._connections_test_serialized_content[db_name]

    @classmethod
    def tearDownClass(cls):
        super(TestSerializedContentMockMixin, cls).tearDownClass()

        # Cleaning any data that has been created by our mixin class
        # to not impact any other django suite test.
        json_data = json.loads(cls.initial_data_migration)
        for data in json_data:
            Klass = apps.get_model(*data['model'].split('.'))
            Klass.objects.get(pk=data['pk']).delete()


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


class TestDataConsistencyOnTearDown(TestSerializedContentMockMixin, TransactionTestCase):
    """
    Initial data should be recreated in TransactionTestCase._fixture_teardown()
    after the database is flushed so it's available in all tests.
    """
    available_apps = ['test_utils']
    serialized_rollback = True
    initial_data_migration = '[{"model": "test_utils.car", "pk": 666, "fields": {"name": "K 2000"}}]'

    def _post_teardown(self):
        super(TestDataConsistencyOnTearDown, self)._post_teardown()
        self.assertTrue(Car.objects.exists())

    def test_that_should_be_the_only_one_in_this_test_case(self):
        pass
