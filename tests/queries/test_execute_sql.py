from unittest import mock

from django.db import DatabaseError, connection
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query
from django.test import TestCase


class ExecuteSqlCursorCloseErrorTests(TestCase):
    def test_execute_sql_preserves_original_exception_when_close_fails(self):
        query = Query(None)
        compiler = SQLCompiler(query, connection, None)
        cursor = mock.MagicMock()

        # Execution fails
        execute_err = DatabaseError("execute failed")
        cursor.execute.side_effect = execute_err

        # Closing fails
        cursor.close.side_effect = DatabaseError("close failed")

        with mock.patch.object(connection, "cursor", return_value=cursor):
            with self.assertRaises(DatabaseError) as ctx:
                compiler.execute_sql("SELECT 1", [])

        exc = ctx.exception
        assert exc is execute_err
        assert exc.__cause__ is None
        assert exc.__suppress_context__ is True
