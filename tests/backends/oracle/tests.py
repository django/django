import unittest

from django.db import connection


@unittest.skipUnless(connection.vendor == 'oracle', 'Oracle tests')
class Tests(unittest.TestCase):

    def test_quote_name(self):
        """'%' chars are escaped for query execution."""
        name = '"SOME%NAME"'
        quoted_name = connection.ops.quote_name(name)
        self.assertEqual(quoted_name % (), name)

    def test_dbms_session(self):
        """A stored procedure can be called through a cursor wrapper."""
        with connection.cursor() as cursor:
            cursor.callproc('DBMS_SESSION.SET_IDENTIFIER', ['_django_testing!'])

    def test_cursor_var(self):
        """Cursor variables can be passed as query parameters."""
        from django.db.backends.oracle.base import Database
        with connection.cursor() as cursor:
            var = cursor.var(Database.STRING)
            cursor.execute("BEGIN %s := 'X'; END; ", [var])
            self.assertEqual(var.getvalue(), 'X')

    def test_long_string(self):
        """Text longer than 4000 chars can be saved and read."""
        with connection.cursor() as cursor:
            cursor.execute('CREATE TABLE ltext ("TEXT" NCLOB)')
            long_str = ''.join(str(x) for x in range(4000))
            cursor.execute('INSERT INTO ltext VALUES (%s)', [long_str])
            cursor.execute('SELECT text FROM ltext')
            row = cursor.fetchone()
            self.assertEqual(long_str, row[0].read())
            cursor.execute('DROP TABLE ltext')

    def test_client_encoding(self):
        """Client encoding is set correctly."""
        connection.ensure_connection()
        self.assertEqual(connection.connection.encoding, 'UTF-8')
        self.assertEqual(connection.connection.nencoding, 'UTF-8')

    def test_order_of_nls_parameters(self):
        """
        An 'almost right' datetime works with configured NLS parameters
        (#18465).
        """
        with connection.cursor() as cursor:
            query = "select 1 from dual where '1936-12-29 00:00' < sysdate"
            # The query succeeds without errors - pre #18465 this
            # wasn't the case.
            cursor.execute(query)
            self.assertEqual(cursor.fetchone()[0], 1)
