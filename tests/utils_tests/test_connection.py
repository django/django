import asyncio
import threading
from unittest.mock import AsyncMock, Mock

from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils.connection import (
    BaseConnectionHandler,
    AbstractConnectionHandler,
    ConnectionDoesNotExist,
    BaseAsyncConnectionHandler,
)


default_settings = {
    "first": {
        "key": "value1",
    },
    "second": {
        "key": "value2",
    },
}


class Connection:
    def __init__(self, alias):
        self.alias = alias
        self.close = Mock()


class AsyncConnection:
    def __init__(self, alias):
        self.alias = alias
        self.close = AsyncMock()


class AbstractConnectionHandlerExample(AbstractConnectionHandler):
    def create_connection(self, alias):
        return Connection(alias)


class BaseConnectionHandlerExample(BaseConnectionHandler):
    def create_connection(self, alias):
        return Connection(alias)


class BaseAsyncConnectionHandlerExample(BaseAsyncConnectionHandler):
    def create_connection(self, alias):
        return AsyncConnection(alias)


class AbstractConnectionHandlerTest(SimpleTestCase):
    def setUp(self):
        self.handler = AbstractConnectionHandlerExample(default_settings)

    def test_settings_from_class(self):
        self.assertEqual(self.handler.settings, default_settings)

    @override_settings(setting_name=default_settings)
    def test_settings_from_django_config(self):
        class CustomNameConnectorHandler(AbstractConnectionHandlerExample):
            settings_name = "setting_name"

        handler = CustomNameConnectorHandler()
        self.assertEqual(handler.settings, default_settings)

    def test_create_connection(self):
        class ConnectionHandler(AbstractConnectionHandler):
            def create_connection(self, alias):
                return super().create_connection(alias)

        msg = "Subclasses must implement create_connection()."
        with self.assertRaisesMessage(NotImplementedError, msg):
            ConnectionHandler().create_connection(None)

    def test_iter(self):
        self.assertEqual(list(self.handler), list(default_settings))

    def test_getitem(self):
        conn1 = self.handler["first"]
        self.assertEqual(conn1.alias, "first")
        self.assertEqual(id(conn1), id(self.handler["first"]))

        conn2 = self.handler["second"]
        self.assertEqual(conn2.alias, "second")
        self.assertEqual(id(conn2), id(self.handler["second"]))

    def test_getitem_wrong_alias(self):
        msg = "The connection 'wrong_alias' doesn't exist."
        with self.assertRaisesRegex(ConnectionDoesNotExist, msg):
            self.handler["wrong_alias"]

    def test_setitem(self):
        conn = Connection("my custom")
        self.handler["first"] = conn

        self.assertEqual(self.handler["first"], conn)

    def test_delitem(self):
        conn = self.handler["first"]
        del self.handler["first"]

        self.assertNotEqual(conn, self.handler["first"])

    def test_all(self):
        connections = self.handler.all()

        self.assertEqual(len(connections), 2)

        conn1, conn2 = connections
        self.assertEqual(conn1.alias, "first")
        self.assertEqual(conn2.alias, "second")

    def test_all_initialized_only(self):
        self.assertEqual(self.handler.all(initialized_only=True), [])


class BaseConnectionHandlerTests(SimpleTestCase):
    def setUp(self):
        self.handler = BaseConnectionHandlerExample(default_settings)

    def test_close_all(self):
        conn1 = self.handler["first"]
        conn2 = self.handler["second"]

        conn1.close.assert_not_called()
        conn2.close.assert_not_called()

        self.handler.close_all()

        conn1.close.assert_called_once_with()
        conn2.close.assert_called_once_with()


class BaseAsyncConnectionHandlerTest(SimpleTestCase):
    def setUp(self):
        self.handler = BaseAsyncConnectionHandlerExample(default_settings)

    async def test_close_all(self):
        conn1 = self.handler["first"]
        conn2 = self.handler["second"]

        conn1.close.assert_not_called()
        conn2.close.assert_not_called()

        await self.handler.close_all()

        conn1.close.assert_called_once_with()
        conn2.close.assert_called_once_with()

    async def test_independent_connection_async_concurrent(self):
        connections = []
        origin_conn = self.handler["first"]

        async def load():
            self.assertEqual(origin_conn, self.handler["first"])

            async with self.handler.independent_connection():
                connections.append(self.handler["first"])

        await asyncio.gather(load(), load(), load())
        connections_ids = set([id(conn) for conn in connections])

        self.assertEqual(len(connections_ids), 3)
        self.assertEqual(len(connections_ids | {id(origin_conn)} ), 4)

        for conn in connections:
            conn.close.assert_called_once_with()

        self.assertEqual(origin_conn, self.handler["first"])

    async def test_independent_connection_nested(self):
        connections = []
        origin_conn = self.handler["first"]

        async with self.handler.independent_connection():
            conn1 = self.handler["first"]
            connections.append(conn1)

            async with self.handler.independent_connection():
                conn2 = self.handler["first"]
                connections.append(conn2)
                self.assertNotEqual(conn1, conn2)

            self.assertEqual(conn1, self.handler["first"])

            async with self.handler.independent_connection():
                conn3 = self.handler["first"]
                connections.append(conn3)
                self.assertNotEqual(conn1, conn3)

            self.assertEqual(conn1, self.handler["first"])

        connections_ids = set([id(conn) for conn in connections])

        self.assertEqual(len(connections_ids), 3)
        self.assertEqual(len(connections_ids | {id(origin_conn)} ), 4)

        for conn in connections:
            conn.close.assert_called_once_with()

        self.assertEqual(origin_conn, self.handler["first"])

    async def test_independent_connection_with_exception(self):
        class AsyncConnectionWithException:
            def __init__(self, alias):
                self.alias = alias
                self.close = AsyncMock()
                self.close.side_effect = Exception

        class BaseAsyncConnectionHandlerWithError(BaseAsyncConnectionHandlerExample):
            def create_connection(self, alias):
                return AsyncConnectionWithException(alias)

        handler = BaseAsyncConnectionHandlerWithError(default_settings)
        origin_conn = handler["first"]
        connections = []

        async def load():
            async with handler.independent_connection():
                connections.append(handler["first"])

        with self.assertRaises(Exception):
            await asyncio.create_task(load())

        with self.assertRaises(Exception):
            async with handler.independent_connection():
                connections.append(handler["first"])

        connections_ids = set([id(conn) for conn in connections])

        self.assertEqual(len(connections_ids), 2)
        self.assertEqual(len(connections_ids | {id(origin_conn)} ), 3)

        for conn in connections:
            conn.close.assert_called_once_with()

        self.assertEqual(origin_conn, handler["first"])

    async def test_thread_critical_for_threads(self):
        origin_connections_map = {}
        separate_connections_map = {}

        origin_connections_map["first"] = self.handler["first"]

        def target():
            separate_connections_map["first"] = self.handler["first"]
            separate_connections_map["second"] = self.handler["second"]

        t = threading.Thread(target=target)
        t.start()
        t.join()

        origin_connections_map["second"] = self.handler["second"]

        self.assertNotEqual(
            origin_connections_map["first"],
            separate_connections_map["first"],
        )
        self.assertNotEqual(
            origin_connections_map["second"],
            separate_connections_map["second"],
        )

    async def test_thread_critical_for_coroutines(self):
        origin_connections_map = {}
        separate_connections_map = {}

        origin_connections_map["first"] = self.handler["first"]

        async def load():
            separate_connections_map["first"] = self.handler["first"]
            separate_connections_map["second"] = self.handler["second"]

        await asyncio.create_task(load())

        origin_connections_map["second"] = self.handler["second"]

        self.assertEqual(
            origin_connections_map["first"],
            separate_connections_map["first"],
        )
        self.assertNotEqual(
            origin_connections_map["second"],
            separate_connections_map["second"],
        )
