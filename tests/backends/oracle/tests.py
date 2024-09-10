import copy
import unittest
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, NotSupportedError, ProgrammingError, connection
from django.db.models import BooleanField
from django.test import TestCase, TransactionTestCase

from ..models import Square, VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ

try:
    from django.db.backends.oracle.oracledb_any import is_oracledb
except ImportError:
    is_oracledb = False


def no_pool_connection(alias=None):
    new_connection = connection.copy(alias)
    new_connection.settings_dict = copy.deepcopy(connection.settings_dict)
    # Ensure that the second connection circumvents the pool, this is kind
    # of a hack, but we cannot easily change the pool connections.
    new_connection.settings_dict["OPTIONS"]["pool"] = False
    return new_connection


@unittest.skipUnless(connection.vendor == "oracle", "Oracle tests")
class Tests(TestCase):
    def test_quote_name(self):
        """'%' chars are escaped for query execution."""
        name = '"SOME%NAME"'
        quoted_name = connection.ops.quote_name(name)
        self.assertEqual(quoted_name % (), name)

    def test_quote_name_db_table(self):
        model = VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ
        db_table = model._meta.db_table.upper()
        self.assertEqual(
            f'"{db_table}"',
            connection.ops.quote_name(
                "backends_verylongmodelnamezzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
            ),
        )

    def test_dbms_session(self):
        """A stored procedure can be called through a cursor wrapper."""
        with connection.cursor() as cursor:
            cursor.callproc("DBMS_SESSION.SET_IDENTIFIER", ["_django_testing!"])

    def test_cursor_var(self):
        """Cursor variables can be passed as query parameters."""
        with connection.cursor() as cursor:
            var = cursor.var(str)
            cursor.execute("BEGIN %s := 'X'; END; ", [var])
            self.assertEqual(var.getvalue(), "X")

    def test_order_of_nls_parameters(self):
        """
        An 'almost right' datetime works with configured NLS parameters
        (#18465).
        """
        suffix = connection.features.bare_select_suffix
        with connection.cursor() as cursor:
            query = f"SELECT 1{suffix} WHERE '1936-12-29 00:00' < SYSDATE"
            # The query succeeds without errors - pre #18465 this
            # wasn't the case.
            cursor.execute(query)
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_boolean_constraints(self):
        """Boolean fields have check constraints on their values."""
        for field in (BooleanField(), BooleanField(null=True)):
            with self.subTest(field=field):
                field.set_attributes_from_name("is_nice")
                self.assertIn('"IS_NICE" IN (0,1)', field.db_check(connection))

    @mock.patch.object(
        connection,
        "get_database_version",
        return_value=(18, 1),
    )
    def test_check_database_version_supported(self, mocked_get_database_version):
        msg = "Oracle 19 or later is required (found 18.1)."
        with self.assertRaisesMessage(NotSupportedError, msg):
            connection.check_database_version_supported()
        self.assertTrue(mocked_get_database_version.called)

    @unittest.skipUnless(is_oracledb, "Pool specific tests")
    def test_pool_set_to_true(self):
        new_connection = no_pool_connection(alias="default_pool")
        new_connection.settings_dict["OPTIONS"]["pool"] = True
        try:
            self.assertIsNotNone(new_connection.pool)
        finally:
            new_connection.close_pool()

    @unittest.skipUnless(is_oracledb, "Pool specific tests")
    def test_pool_reuse(self):
        new_connection = no_pool_connection(alias="default_pool")
        new_connection.settings_dict["OPTIONS"]["pool"] = {
            "min": 0,
            "max": 2,
        }
        self.assertIsNotNone(new_connection.pool)

        connections = []

        def get_connection():
            # copy() reuses the existing alias and as such the same pool.
            conn = new_connection.copy()
            conn.connect()
            connections.append(conn)
            return conn

        try:
            connection_1 = get_connection()  # First connection.
            get_connection()  # Get the second connection.
            sql = "select sys_context('userenv', 'sid') from dual"
            sids = [conn.cursor().execute(sql).fetchone()[0] for conn in connections]
            connection_1.close()  # Release back to the pool.
            connection_3 = get_connection()
            sid = connection_3.cursor().execute(sql).fetchone()[0]
            # Reuses the first connection as it is available.
            self.assertEqual(sid, sids[0])
        finally:
            # Release all connections back to the pool.
            for conn in connections:
                conn.close()
            new_connection.close_pool()

    @unittest.skipUnless(is_oracledb, "Pool specific tests")
    def test_cannot_open_new_connection_in_atomic_block(self):
        new_connection = no_pool_connection(alias="default_pool")
        new_connection.settings_dict["OPTIONS"]["pool"] = True
        msg = "Cannot open a new connection in an atomic block."
        new_connection.in_atomic_block = True
        new_connection.closed_in_transaction = True
        with self.assertRaisesMessage(ProgrammingError, msg):
            new_connection.ensure_connection()

    @unittest.skipUnless(is_oracledb, "Pool specific tests")
    def test_pooling_not_support_persistent_connections(self):
        new_connection = no_pool_connection(alias="default_pool")
        new_connection.settings_dict["OPTIONS"]["pool"] = True
        new_connection.settings_dict["CONN_MAX_AGE"] = 10
        msg = "Pooling doesn't support persistent connections."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            new_connection.pool

    @unittest.skipIf(is_oracledb, "cx_oracle specific tests")
    def test_cx_Oracle_not_support_pooling(self):
        new_connection = no_pool_connection()
        new_connection.settings_dict["OPTIONS"]["pool"] = True
        msg = "Pooling isn't supported by cx_Oracle. Use python-oracledb instead."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            new_connection.connect()


@unittest.skipUnless(connection.vendor == "oracle", "Oracle tests")
class TransactionalTests(TransactionTestCase):
    available_apps = ["backends"]

    def test_hidden_no_data_found_exception(self):
        # "ORA-1403: no data found" exception is hidden by Oracle OCI library
        # when an INSERT statement is used with a RETURNING clause (see #28859).
        with connection.cursor() as cursor:
            # Create trigger that raises "ORA-1403: no data found".
            cursor.execute(
                """
                CREATE OR REPLACE TRIGGER "TRG_NO_DATA_FOUND"
                AFTER INSERT ON "BACKENDS_SQUARE"
                FOR EACH ROW
                BEGIN
                    RAISE NO_DATA_FOUND;
                END;
            """
            )
        try:
            with self.assertRaisesMessage(
                DatabaseError,
                (
                    'The database did not return a new row id. Probably "ORA-1403: no '
                    'data found" was raised internally but was hidden by the Oracle '
                    "OCI library (see https://code.djangoproject.com/ticket/28859)."
                ),
            ):
                Square.objects.create(root=2, square=4)
        finally:
            with connection.cursor() as cursor:
                cursor.execute('DROP TRIGGER "TRG_NO_DATA_FOUND"')

    def test_password_with_at_sign(self):
        from django.db.backends.oracle.base import Database

        old_password = connection.settings_dict["PASSWORD"]
        connection.settings_dict["PASSWORD"] = "p@ssword"
        try:
            self.assertIn(
                '/"p@ssword"@',
                connection.client.connect_string(connection.settings_dict),
            )
            with self.assertRaises(Database.DatabaseError) as context:
                connection.connect()
            # Database exception: "ORA-01017: invalid username/password" is
            # expected.
            self.assertIn("ORA-01017", context.exception.args[0].message)
        finally:
            connection.settings_dict["PASSWORD"] = old_password
