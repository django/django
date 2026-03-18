from unittest import mock

from django.db import DEFAULT_DB_ALIAS, DatabaseError, connection
from django.db.models.sql import Query
from django.db.models.sql.compiler import SQLCompiler
from django.test import TestCase

from .models import Item


class SQLCompilerTest(TestCase):
    def test_repr(self):
        query = Query(Item)
        compiler = query.get_compiler(DEFAULT_DB_ALIAS, connection)
        self.assertEqual(
            repr(compiler),
            f"<SQLCompiler model=Item connection="
            f"<DatabaseWrapper vendor={connection.vendor!r} alias='default'> "
            f"using='default'>",
        )

    def test_execute_sql_suppresses_cursor_closing_failure_on_exception(self):
        query = Query(Item)
        compiler = SQLCompiler(query, connection, None)
        cursor = mock.MagicMock()

        # When execution fails, the cursor may have been closed.
        # Django's attempt to close it again will fail, and needs catching.
        execute_err = DatabaseError("execute failed")
        cursor.execute.side_effect = execute_err
        cursor.close.side_effect = DatabaseError("close failed")

        with mock.patch.object(connection, "cursor", return_value=cursor):
            with self.assertRaises(DatabaseError) as ctx:
                compiler.execute_sql("SELECT 1", [])

        # There is no irrelevant context from trying to close a closed cursor.
        exc = ctx.exception
        self.assertIs(exc, execute_err)
        self.assertIsNone(exc.__cause__)
        self.assertTrue(exc.__suppress_context__)
