from unittest import mock

from django.db import DatabaseError, connection, models
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.query import Query
from django.test import TestCase


class DummyModel(models.Model):
    class Meta:
        app_label = "tests"
        managed = False


class ExecuteSqlCursorCloseErrorTests(TestCase):
    def test_execute_sql_raises_original_exception_when_close_fails(self):
        # Build compiler
        query = Query(DummyModel)
        compiler = SQLCompiler(query, connection, None)

        # Fake cursor
        cursor = mock.MagicMock()

        # Step 1: execution fails
        execute_err = DatabaseError("execute failed")
        cursor.execute.side_effect = execute_err

        # Step 2: closing fails
        cursor.close.side_effect = DatabaseError("close failed")

        # Patch connection.cursor() to use our fake cursor
        with mock.patch.object(connection, "cursor", return_value=cursor):
            with self.assertRaises(DatabaseError) as ctx:
                compiler.execute_sql("SELECT 1", [])

        # Must be *execute* error, not close error
        assert str(ctx.exception) == "execute failed"
