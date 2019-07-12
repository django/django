import datetime
import unittest

from django.db import connection
from django.db.models.fields import BooleanField, NullBooleanField
from django.db.utils import DatabaseError
from django.test import TransactionTestCase

from ..models import NonIntegerAutoField, Square


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
        with connection.cursor() as cursor:
            var = cursor.var(str)
            cursor.execute("BEGIN %s := 'X'; END; ", [var])
            self.assertEqual(var.getvalue(), 'X')

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

    def test_boolean_constraints(self):
        """Boolean fields have check constraints on their values."""
        for field in (BooleanField(), NullBooleanField(), BooleanField(null=True)):
            with self.subTest(field=field):
                field.set_attributes_from_name('is_nice')
                self.assertIn('"IS_NICE" IN (0,1)', field.db_check(connection))


@unittest.skipUnless(connection.vendor == 'oracle', 'Oracle tests')
class TransactionalTests(TransactionTestCase):
    available_apps = ['backends']

    def test_hidden_no_data_found_exception(self):
        # "ORA-1403: no data found" exception is hidden by Oracle OCI library
        # when an INSERT statement is used with a RETURNING clause (see #28859).
        with connection.cursor() as cursor:
            # Create trigger that raises "ORA-1403: no data found".
            cursor.execute("""
                CREATE OR REPLACE TRIGGER "TRG_NO_DATA_FOUND"
                AFTER INSERT ON "BACKENDS_SQUARE"
                FOR EACH ROW
                BEGIN
                    RAISE NO_DATA_FOUND;
                END;
            """)
        try:
            with self.assertRaisesMessage(DatabaseError, (
                'The database did not return a new row id. Probably "ORA-1403: '
                'no data found" was raised internally but was hidden by the '
                'Oracle OCI library (see https://code.djangoproject.com/ticket/28859).'
            )):
                Square.objects.create(root=2, square=4)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP TRIGGER "TRG_NO_DATA_FOUND"')

    def test_password_with_at_sign(self):
        old_password = connection.settings_dict['PASSWORD']
        connection.settings_dict['PASSWORD'] = 'p@ssword'
        try:
            self.assertIn('/"p@ssword"@', connection._connect_string())
            with self.assertRaises(DatabaseError) as context:
                connection.cursor()
            # Database exception: "ORA-01017: invalid username/password" is
            # expected.
            self.assertIn('ORA-01017', context.exception.args[0].message)
        finally:
            connection.settings_dict['PASSWORD'] = old_password

    def test_non_integer_auto_field(self):
        with connection.cursor() as cursor:
            # Create trigger that fill non-integer auto field.
            cursor.execute("""
                CREATE OR REPLACE TRIGGER "TRG_FILL_CREATION_DATETIME"
                BEFORE INSERT ON "BACKENDS_NONINTEGERAUTOFIELD"
                FOR EACH ROW
                BEGIN
                    :NEW.CREATION_DATETIME := SYSTIMESTAMP;
                END;
            """)
        try:
            NonIntegerAutoField._meta.auto_field = NonIntegerAutoField.creation_datetime
            obj = NonIntegerAutoField.objects.create()
            self.assertIsNotNone(obj.creation_datetime)
            self.assertIsInstance(obj.creation_datetime, datetime.datetime)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP TRIGGER "TRG_FILL_CREATION_DATETIME"')
