"""Tests for django.db.utils."""

import asyncio
import concurrent.futures
import unittest
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.db import (
    DEFAULT_DB_ALIAS,
    ProgrammingError,
    async_connections,
    connection,
    new_connection,
)
from django.db.utils import (
    AsyncAlias,
    AsyncConnectionHandler,
    ConnectionHandler,
    load_backend,
)
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
        from django.db.backends.postgresql.psycopg_any import is_psycopg3

        with connection.cursor() as cursor:
            msg = 'table "X" does not exist'
            with self.assertRaisesMessage(ProgrammingError, msg) as cm:
                cursor.execute('DROP TABLE "X"')
        self.assertNotEqual(type(cm.exception), type(cm.exception.__cause__))
        self.assertIsNotNone(cm.exception.__cause__)
        if is_psycopg3:
            self.assertIsNotNone(cm.exception.__cause__.diag.sqlstate)
            self.assertIsNotNone(cm.exception.__cause__.diag.message_primary)
        else:
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


class AsyncConnectionTests(SimpleTestCase):
    def run_pool(self, coro, count=2):
        def fn():
            asyncio.run(coro())

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for _ in range(count):
                futures.append(executor.submit(fn))

            for future in concurrent.futures.as_completed(futures):
                exc = future.exception()
                if exc is not None:
                    raise exc

    def test_async_alias(self):
        alias = AsyncAlias()
        assert len(alias) == 0
        assert alias.connections == []

        async def coro():
            assert len(alias) == 0
            alias.add_connection(mock.Mock())
            alias.pop()

        self.run_pool(coro)

    def test_async_connection_handler(self):
        aconns = AsyncConnectionHandler()
        assert aconns.empty is True
        assert aconns["default"].connections == []

        async def coro():
            assert aconns["default"].connections == []
            aconns.add_connection("default", mock.Mock())
            aconns.pop_connection("default")

        self.run_pool(coro)

    @unittest.skipUnless(connection.supports_async is True, "Async DB test")
    def test_new_connection_threading(self):
        async def coro():
            assert async_connections.empty is True
            async with new_connection() as connection:
                async with connection.acursor() as c:
                    await c.execute("SELECT 1")

        self.run_pool(coro)

    @unittest.skipUnless(connection.supports_async is True, "Async DB test")
    async def test_new_connection(self):
        with self.assertRaises(ConnectionDoesNotExist):
            async_connections.get_connection(DEFAULT_DB_ALIAS)

        async with new_connection():
            conn1 = async_connections.get_connection(DEFAULT_DB_ALIAS)
            async with new_connection():
                conn2 = async_connections.get_connection(DEFAULT_DB_ALIAS)
                self.assertNotEqual(conn1, conn2)
            self.assertNotEqual(conn1, conn2)
        with self.assertRaises(ConnectionDoesNotExist):
            async_connections.get_connection(DEFAULT_DB_ALIAS)
