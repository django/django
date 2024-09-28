import unittest
from unittest import mock

from django.db import DatabaseError, NotSupportedError, connection
from django.db.models import BooleanField
from django.test import TestCase, TransactionTestCase

from ..models import Square, VeryLongModelNameZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ


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
