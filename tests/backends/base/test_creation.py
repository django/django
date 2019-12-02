import copy
from unittest import mock

from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.creation import (
    TEST_DATABASE_PREFIX, BaseDatabaseCreation,
)
from django.test import SimpleTestCase

from ..models import (
    Author, Book, CircularRefThingA, CircularRefThingB, SelfRefThing,
)


def get_connection_copy():
    # Get a copy of the default connection. (Can't use django.db.connection
    # because it'll modify the default connection itself.)
    test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
    test_connection.settings_dict = copy.deepcopy(
        connections[DEFAULT_DB_ALIAS].settings_dict
    )
    return test_connection


class TestDbSignatureTests(SimpleTestCase):
    def test_default_name(self):
        # A test db name isn't set.
        prod_name = 'hodor'
        test_connection = get_connection_copy()
        test_connection.settings_dict['NAME'] = prod_name
        test_connection.settings_dict['TEST'] = {'NAME': None}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], TEST_DATABASE_PREFIX + prod_name)

    def test_custom_test_name(self):
        # A regular test db name is set.
        test_name = 'hodor'
        test_connection = get_connection_copy()
        test_connection.settings_dict['TEST'] = {'NAME': test_name}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], test_name)

    def test_custom_test_name_with_test_prefix(self):
        # A test db name prefixed with TEST_DATABASE_PREFIX is set.
        test_name = TEST_DATABASE_PREFIX + 'hodor'
        test_connection = get_connection_copy()
        test_connection.settings_dict['TEST'] = {'NAME': test_name}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], test_name)


@mock.patch.object(connection, 'ensure_connection')
@mock.patch('django.core.management.commands.migrate.Command.handle', return_value=None)
class TestDbCreationTests(SimpleTestCase):
    def test_migrate_test_setting_false(self, mocked_migrate, mocked_ensure_connection):
        test_connection = get_connection_copy()
        test_connection.settings_dict['TEST']['MIGRATE'] = False
        creation = test_connection.creation_class(test_connection)
        old_database_name = test_connection.settings_dict['NAME']
        try:
            with mock.patch.object(creation, '_create_test_db'):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            mocked_migrate.assert_not_called()
        finally:
            with mock.patch.object(creation, '_destroy_test_db'):
                creation.destroy_test_db(old_database_name, verbosity=0)

    def test_migrate_test_setting_true(self, mocked_migrate, mocked_ensure_connection):
        test_connection = get_connection_copy()
        test_connection.settings_dict['TEST']['MIGRATE'] = True
        creation = test_connection.creation_class(test_connection)
        old_database_name = test_connection.settings_dict['NAME']
        try:
            with mock.patch.object(creation, '_create_test_db'):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            mocked_migrate.assert_called_once()
        finally:
            with mock.patch.object(creation, '_destroy_test_db'):
                creation.destroy_test_db(old_database_name, verbosity=0)


class TestDeserializeDbFromString(SimpleTestCase):
    databases = ['default']

    def test_forward_reference(self):
        """
        This has the book before the author it references, to verify deserialize_db_from_string handles this properly
        (regression test for #26552).
        """

        serialized = """
        [
            {"model": "backends.book", "pk": 1, "fields": {"author": "John"}},
            {"model": "backends.author", "pk": 1, "fields": {"name": "John"}}
        ]
        """
        creation = connection.creation_class(connection)
        creation.deserialize_db_from_string(serialized)

        # Check that deserialization actually worked (in addition to not failing)
        a = Author.objects.get()
        b = Book.objects.get()
        self.assertEqual(b.author, a)

    def test_serialize_circular_ref(self):
        """ This serializes and deserializes circular and self-referencing models (regression test for #31051). """

        # Add some self-referencing data
        a = CircularRefThingA.objects.create(key="X")
        b = CircularRefThingB.objects.create(key="Y", other_thing=a)
        a.other_thing = b
        a.save()

        t1 = SelfRefThing.objects.create(key="X")
        t2 = SelfRefThing.objects.create(key="Y", other_thing=t1)
        t1.other_thing = t2
        t1.save()

        # This mimics parts of the test runner process, which serializes during db creation, flush after each testcase,
        # deserialize before the next testcase.
        creation = connection.creation_class(connection)

        with mock.patch('django.db.migrations.loader.MigrationLoader') as loader:
            # serialize_db_to_string only serializes apps that have migrations, so pretend that (only) we do
            loader_instance = loader.return_value
            loader_instance.migrated_apps = set(['backends'])
            serialized = creation.serialize_db_to_string()

        call_command('flush', verbosity=0, interactive=False, database=DEFAULT_DB_ALIAS, reset_sequences=False,
                     inhibit_post_migrate=True)

        creation.deserialize_db_from_string(serialized)

        # Check that deserialization actually worked for the objects we're interested in
        a = CircularRefThingA.objects.get()
        b = CircularRefThingB.objects.get()
        self1, self2 = SelfRefThing.objects.all()
        self.assertEqual(a.other_thing, b)
        self.assertEqual(b.other_thing, a)
        self.assertEqual(self1.other_thing, self2)
        self.assertEqual(self2.other_thing, self1)
