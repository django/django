import copy
import datetime
import os
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.creation import TEST_DATABASE_PREFIX, BaseDatabaseCreation
from django.test import SimpleTestCase, TransactionTestCase
from django.test.utils import override_settings

from ..models import (
    CircularA,
    CircularB,
    Object,
    ObjectReference,
    ObjectSelfReference,
    SchoolClass,
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
        prod_name = "hodor"
        test_connection = get_connection_copy()
        test_connection.settings_dict["NAME"] = prod_name
        test_connection.settings_dict["TEST"] = {"NAME": None}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], TEST_DATABASE_PREFIX + prod_name)

    def test_custom_test_name(self):
        # A regular test db name is set.
        test_name = "hodor"
        test_connection = get_connection_copy()
        test_connection.settings_dict["TEST"] = {"NAME": test_name}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], test_name)

    def test_custom_test_name_with_test_prefix(self):
        # A test db name prefixed with TEST_DATABASE_PREFIX is set.
        test_name = TEST_DATABASE_PREFIX + "hodor"
        test_connection = get_connection_copy()
        test_connection.settings_dict["TEST"] = {"NAME": test_name}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], test_name)


@override_settings(INSTALLED_APPS=["backends.base.app_unmigrated"])
@mock.patch.object(connection, "ensure_connection")
@mock.patch.object(connection, "prepare_database")
@mock.patch(
    "django.db.migrations.recorder.MigrationRecorder.has_table", return_value=False
)
@mock.patch("django.core.management.commands.migrate.Command.sync_apps")
class TestDbCreationTests(SimpleTestCase):
    available_apps = ["backends.base.app_unmigrated"]

    @mock.patch("django.db.migrations.executor.MigrationExecutor.migrate")
    def test_migrate_test_setting_false(
        self, mocked_migrate, mocked_sync_apps, *mocked_objects
    ):
        test_connection = get_connection_copy()
        test_connection.settings_dict["TEST"]["MIGRATE"] = False
        creation = test_connection.creation_class(test_connection)
        if connection.vendor == "oracle":
            # Don't close connection on Oracle.
            creation.connection.close = mock.Mock()
        old_database_name = test_connection.settings_dict["NAME"]
        try:
            with mock.patch.object(creation, "_create_test_db"):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            # Migrations don't run.
            mocked_migrate.assert_called()
            args, kwargs = mocked_migrate.call_args
            self.assertEqual(args, ([],))
            self.assertEqual(kwargs["plan"], [])
            # App is synced.
            mocked_sync_apps.assert_called()
            mocked_args, _ = mocked_sync_apps.call_args
            self.assertEqual(mocked_args[1], {"app_unmigrated"})
        finally:
            with mock.patch.object(creation, "_destroy_test_db"):
                creation.destroy_test_db(old_database_name, verbosity=0)

    @mock.patch("django.db.migrations.executor.MigrationRecorder.ensure_schema")
    def test_migrate_test_setting_false_ensure_schema(
        self,
        mocked_ensure_schema,
        mocked_sync_apps,
        *mocked_objects,
    ):
        test_connection = get_connection_copy()
        test_connection.settings_dict["TEST"]["MIGRATE"] = False
        creation = test_connection.creation_class(test_connection)
        if connection.vendor == "oracle":
            # Don't close connection on Oracle.
            creation.connection.close = mock.Mock()
        old_database_name = test_connection.settings_dict["NAME"]
        try:
            with mock.patch.object(creation, "_create_test_db"):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            # The django_migrations table is not created.
            mocked_ensure_schema.assert_not_called()
            # App is synced.
            mocked_sync_apps.assert_called()
            mocked_args, _ = mocked_sync_apps.call_args
            self.assertEqual(mocked_args[1], {"app_unmigrated"})
        finally:
            with mock.patch.object(creation, "_destroy_test_db"):
                creation.destroy_test_db(old_database_name, verbosity=0)

    @mock.patch("django.db.migrations.executor.MigrationExecutor.migrate")
    def test_migrate_test_setting_true(
        self, mocked_migrate, mocked_sync_apps, *mocked_objects
    ):
        test_connection = get_connection_copy()
        test_connection.settings_dict["TEST"]["MIGRATE"] = True
        creation = test_connection.creation_class(test_connection)
        if connection.vendor == "oracle":
            # Don't close connection on Oracle.
            creation.connection.close = mock.Mock()
        old_database_name = test_connection.settings_dict["NAME"]
        try:
            with mock.patch.object(creation, "_create_test_db"):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            # Migrations run.
            mocked_migrate.assert_called()
            args, kwargs = mocked_migrate.call_args
            self.assertEqual(args, ([("app_unmigrated", "0001_initial")],))
            self.assertEqual(len(kwargs["plan"]), 1)
            # App is not synced.
            mocked_sync_apps.assert_not_called()
        finally:
            with mock.patch.object(creation, "_destroy_test_db"):
                creation.destroy_test_db(old_database_name, verbosity=0)

    @mock.patch.dict(os.environ, {"RUNNING_DJANGOS_TEST_SUITE": ""})
    @mock.patch("django.db.migrations.executor.MigrationExecutor.migrate")
    @mock.patch.object(BaseDatabaseCreation, "mark_expected_failures_and_skips")
    def test_mark_expected_failures_and_skips_call(
        self, mark_expected_failures_and_skips, *mocked_objects
    ):
        """
        mark_expected_failures_and_skips() isn't called unless
        RUNNING_DJANGOS_TEST_SUITE is 'true'.
        """
        test_connection = get_connection_copy()
        creation = test_connection.creation_class(test_connection)
        if connection.vendor == "oracle":
            # Don't close connection on Oracle.
            creation.connection.close = mock.Mock()
        old_database_name = test_connection.settings_dict["NAME"]
        try:
            with mock.patch.object(creation, "_create_test_db"):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            self.assertIs(mark_expected_failures_and_skips.called, False)
        finally:
            with mock.patch.object(creation, "_destroy_test_db"):
                creation.destroy_test_db(old_database_name, verbosity=0)


class TestDeserializeDbFromString(TransactionTestCase):
    available_apps = ["backends"]

    def test_circular_reference(self):
        # deserialize_db_from_string() handles circular references.
        data = """
        [
            {
                "model": "backends.object",
                "pk": 1,
                "fields": {"obj_ref": 1, "related_objects": []}
            },
            {
                "model": "backends.objectreference",
                "pk": 1,
                "fields": {"obj": 1}
            }
        ]
        """
        connection.creation.deserialize_db_from_string(data)
        obj = Object.objects.get()
        obj_ref = ObjectReference.objects.get()
        self.assertEqual(obj.obj_ref, obj_ref)
        self.assertEqual(obj_ref.obj, obj)

    def test_self_reference(self):
        # serialize_db_to_string() and deserialize_db_from_string() handles
        # self references.
        obj_1 = ObjectSelfReference.objects.create(key="X")
        obj_2 = ObjectSelfReference.objects.create(key="Y", obj=obj_1)
        obj_1.obj = obj_2
        obj_1.save()
        # Serialize objects.
        with mock.patch("django.db.migrations.loader.MigrationLoader") as loader:
            # serialize_db_to_string() serializes only migrated apps, so mark
            # the backends app as migrated.
            loader_instance = loader.return_value
            loader_instance.migrated_apps = {"backends"}
            data = connection.creation.serialize_db_to_string()
        ObjectSelfReference.objects.all().delete()
        # Deserialize objects.
        connection.creation.deserialize_db_from_string(data)
        obj_1 = ObjectSelfReference.objects.get(key="X")
        obj_2 = ObjectSelfReference.objects.get(key="Y")
        self.assertEqual(obj_1.obj, obj_2)
        self.assertEqual(obj_2.obj, obj_1)

    def test_circular_reference_with_natural_key(self):
        # serialize_db_to_string() and deserialize_db_from_string() handles
        # circular references for models with natural keys.
        obj_a = CircularA.objects.create(key="A")
        obj_b = CircularB.objects.create(key="B", obj=obj_a)
        obj_a.obj = obj_b
        obj_a.save()
        # Serialize objects.
        with mock.patch("django.db.migrations.loader.MigrationLoader") as loader:
            # serialize_db_to_string() serializes only migrated apps, so mark
            # the backends app as migrated.
            loader_instance = loader.return_value
            loader_instance.migrated_apps = {"backends"}
            data = connection.creation.serialize_db_to_string()
        CircularA.objects.all().delete()
        CircularB.objects.all().delete()
        # Deserialize objects.
        connection.creation.deserialize_db_from_string(data)
        obj_a = CircularA.objects.get()
        obj_b = CircularB.objects.get()
        self.assertEqual(obj_a.obj, obj_b)
        self.assertEqual(obj_b.obj, obj_a)

    def test_serialize_db_to_string_base_manager(self):
        SchoolClass.objects.create(year=1000, last_updated=datetime.datetime.now())
        with mock.patch("django.db.migrations.loader.MigrationLoader") as loader:
            # serialize_db_to_string() serializes only migrated apps, so mark
            # the backends app as migrated.
            loader_instance = loader.return_value
            loader_instance.migrated_apps = {"backends"}
            data = connection.creation.serialize_db_to_string()
        self.assertIn('"model": "backends.schoolclass"', data)
        self.assertIn('"year": 1000', data)


class SkipTestClass:
    def skip_function(self):
        pass


def skip_test_function():
    pass


def expected_failure_test_function():
    pass


class TestMarkTests(SimpleTestCase):
    def test_mark_expected_failures_and_skips(self):
        test_connection = get_connection_copy()
        creation = BaseDatabaseCreation(test_connection)
        creation.connection.features.django_test_expected_failures = {
            "backends.base.test_creation.expected_failure_test_function",
        }
        creation.connection.features.django_test_skips = {
            "skip test class": {
                "backends.base.test_creation.SkipTestClass",
            },
            "skip test function": {
                "backends.base.test_creation.skip_test_function",
            },
        }
        creation.mark_expected_failures_and_skips()
        self.assertIs(
            expected_failure_test_function.__unittest_expecting_failure__,
            True,
        )
        self.assertIs(SkipTestClass.__unittest_skip__, True)
        self.assertEqual(
            SkipTestClass.__unittest_skip_why__,
            "skip test class",
        )
        self.assertIs(skip_test_function.__unittest_skip__, True)
        self.assertEqual(
            skip_test_function.__unittest_skip_why__,
            "skip test function",
        )
