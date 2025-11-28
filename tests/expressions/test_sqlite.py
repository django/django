from decimal import Decimal
from unittest import skipUnless

from django.db import connection
from django.db.models import DecimalField, Value
from django.db.models.sql import Query
from django.test import TestCase


class SQLiteDecimalExpressionsTests(TestCase):
    # Ensures the test only runs on SQLite.
    @skipUnless(connection.vendor == "sqlite", "SQLite-only test")
    def test_literal_value_decimal_not_cast(self):
        expr = Value(Decimal("3.0"), output_field=DecimalField())

        compiler = connection.ops.compiler("SQLCompiler")(Query(None), connection, None)
        sql, params = expr.resolve_expression(Query(None)).as_sql(compiler, connection)

        self.assertNotIn("CAST(", sql)
        self.assertNotIn("AS NUMERIC", sql)
