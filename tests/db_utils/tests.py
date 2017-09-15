"""Tests for django.db.utils."""
import unittest
from unittest.mock import MagicMock

from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.utils import ConnectionHandler, ProgrammingError, load_backend
from django.test import SimpleTestCase, TestCase


class ConnectionHandlerTests(SimpleTestCase):

    def test_connection_handler_no_databases(self):
        """Empty DATABASES setting defaults to the dummy backend."""
        DATABASES = {}
        conns = ConnectionHandler(DATABASES)
        self.assertEqual(conns[DEFAULT_DB_ALIAS].settings_dict['ENGINE'], 'django.db.backends.dummy')
        msg = (
            'settings.DATABASES is improperly configured. Please supply the '
            'ENGINE value. Check settings documentation for more details.'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            conns[DEFAULT_DB_ALIAS].ensure_connection()


class DatabaseErrorWrapperTests(TestCase):

    @unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL test')
    def test_reraising_backend_specific_database_exception(self):
        cursor = connection.cursor()
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
            "'foo' isn't an available database backend.\n"
            "Try using 'django.db.backends.XXX', where XXX is one of:\n"
            "    'mysql', 'oracle', 'postgresql', 'sqlite3'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg) as cm:
            load_backend('foo')
        self.assertEqual(str(cm.exception.__cause__), "No module named 'foo'")


class ExecuteHookTests(TestCase):

    @staticmethod
    def call_execute(connection, params=None):
        ret_val = '1' if params is None else '%s'
        sql = 'SELECT ' + ret_val + connection.features.bare_select_suffix
        connection.cursor().execute(sql, params)

    def call_executemany(self, connection, params_list=((1,),) * 3):
        sql = 'GIBBERISH %s' + connection.features.bare_select_suffix
        # We need a no-op query, but it has to be DML. We could use a model
        # to make sure there's a table we can update, or we could just catch
        # the error.
        with self.assertRaises(Exception):
            connection.cursor().executemany(sql, params_list)

    def test_hook_invoked(self):
        hook_factory = MagicMock()
        hook_factory.return_value = hook = MagicMock()
        with connection.execute_hook(hook_factory):
            self.call_execute(connection)
        self.assertTrue(hook_factory.called and hook.__enter__.called and hook.__exit__.called)
        _, kwargs = hook_factory.call_args
        self.assertEqual(kwargs['connection'], connection)
        self.assertIn('sql', kwargs)
        self.assertIn('params', kwargs)
        self.assertNotIn('param_list', kwargs)

    def test_hook_invoked_many(self):
        hook_factory = MagicMock()
        hook_factory.return_value = hook = MagicMock()
        with connection.execute_hook(hook_factory):
            self.call_executemany(connection)
        self.assertTrue(hook_factory.called and hook.__enter__.called and hook.__exit__.called)
        _, kwargs = hook_factory.call_args
        self.assertEqual(kwargs['connection'], connection)
        self.assertIn('sql', kwargs)
        self.assertNotIn('params', kwargs)
        self.assertIn('param_list', kwargs)

    def test_noncallable_hook_invoked(self):

        class NonCallableHook:
            __enter__ = MagicMock()
            __exit__ = MagicMock(return_value=None)

        hook = NonCallableHook()
        with connection.execute_hook(hook):
            self.call_execute(connection)
            self.assertEqual((hook.__enter__.call_count, hook.__exit__.call_count), (1, 1))
            self.call_executemany(connection)
            self.assertEqual((hook.__enter__.call_count, hook.__exit__.call_count), (2, 2))

    def test_hook_forsingle(self):
        hook = MagicMock()
        with connection.execute_hook(hook, for_many=False):
            self.call_executemany(connection)
            self.assertFalse(hook.called)
            self.call_execute(connection)
            self.assertTrue(hook.called)

    def test_hook_formany(self):
        hook = MagicMock()
        with connection.execute_hook(hook, for_many=True):
            self.call_execute(connection)
            self.assertFalse(hook.called)
            self.call_executemany(connection)
            self.assertTrue(hook.called)

    def test_hook_gets_sql(self):
        hook = MagicMock()
        sql = "SELECT 'aloha'" + connection.features.bare_select_suffix
        with connection.execute_hook(hook):
            connection.cursor().execute(sql)
        _, kwargs = hook.call_args
        self.assertEqual(kwargs['sql'], sql)

    def test_hook_connection_specific(self):
        hook = MagicMock()
        with connections['other'].execute_hook(hook):
            self.call_execute(connection)
        self.assertFalse(hook.called)
        self.assertEqual(connection.get_execute_hooks(True), [])
        self.assertEqual(connections['other'].get_execute_hooks(False), [])
