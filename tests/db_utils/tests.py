"""Tests for django.db.utils."""
import unittest

from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connection
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
            "'foo' isn't an available database backend.\n"
            "Try using 'django.db.backends.XXX', where XXX is one of:\n"
            "    'mysql', 'oracle', 'postgresql', 'sqlite3'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg) as cm:
            load_backend('foo')
        self.assertEqual(str(cm.exception.__cause__), "No module named 'foo'")
