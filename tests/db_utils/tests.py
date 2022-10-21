"""Tests for django.db.utils."""
import multiprocessing
import unittest

from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, ProgrammingError, connection 
from django.db.utils import ConnectionHandler, load_backend
from django.test import SimpleTestCase, TestCase
from django.utils.connection import ConnectionDoesNotExist


class ConnectionHandlerTests(SimpleTestCase):
    def test_connection_handler_no_databases(self):
        """
        Empty DATABASES and empty 'default' settings default to the dummy
        backend.
        """
        for DATABASES in (
            {},  # Empty DATABASES setting.
            {"default": {}},  # Empty 'default' database.
        ):
            with self.subTest(DATABASES=DATABASES):
                self.assertImproperlyConfigured(DATABASES)

    def assertImproperlyConfigured(self, DATABASES):
        conns = ConnectionHandler(DATABASES)
        self.assertEqual(
            conns[DEFAULT_DB_ALIAS].settings_dict["ENGINE"], "django.db.backends.dummy"
        )
        msg = (
            "settings.DATABASES is improperly configured. Please supply the "
            "ENGINE value. Check settings documentation for more details."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            conns[DEFAULT_DB_ALIAS].ensure_connection()

    def test_no_default_database(self):
        DATABASES = {"other": {}}
        conns = ConnectionHandler(DATABASES)
        msg = "You must define a 'default' database."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            conns["other"].ensure_connection()

    def test_databases_property(self):
        # The "databases" property is maintained for backwards compatibility
        # with 3rd party packages. It should be an alias of the "settings"
        # property.
        conn = ConnectionHandler({})
        self.assertNotEqual(conn.settings, {})
        self.assertEqual(conn.settings, conn.databases)

    def test_nonexistent_alias(self):
        msg = "The connection 'nonexistent' doesn't exist."
        conns = ConnectionHandler(
            {
                DEFAULT_DB_ALIAS: {"ENGINE": "django.db.backends.dummy"},
            }
        )
        with self.assertRaisesMessage(ConnectionDoesNotExist, msg):
            conns["nonexistent"]


class DatabaseErrorWrapperTests(TestCase):
    @unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL test")
    def test_reraising_backend_specific_database_exception(self):
        with connection.cursor() as cursor:
            msg = 'table "X" does not exist'
            with self.assertRaisesMessage(ProgrammingError, msg) as cm:
                cursor.execute('DROP TABLE "X"')
        self.assertNotEqual(type(cm.exception), type(cm.exception.__cause__))
        self.assertIsNotNone(cm.exception.__cause__)
        self.assertIsNotNone(cm.exception.__cause__.pgcode)
        self.assertIsNotNone(cm.exception.__cause__.pgerror)


class LoadBackendTests(SimpleTestCase):
    def test_load_backend_invalid_name(self):
        msg = (
            "'foo' isn't an available database backend or couldn't be "
            "imported. Check the above exception. To use one of the built-in "
            "backends, use 'django.db.backends.XXX', where XXX is one of:\n"
            "    'mysql', 'oracle', 'postgresql', 'sqlite3'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg) as cm:
            load_backend("foo")
        self.assertEqual(str(cm.exception.__cause__), "No module named 'foo'")


def connection_is_open():
    return connection.is_usable()


class DatabaseConnectionForkedProcessTests(SimpleTestCase):
    databases = ["default"]

    @unittest.skipUnless(connection.vendor == "sqlite3", "SQLite connections are always usable")
    def test_connections_closed_on_forked_process(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        with multiprocessing.Pool(1) as pool:
            is_open = pool.apply(connection_is_open)

            self.assertIs(is_open, False)

        self.assertIs(connection_is_open, True)
