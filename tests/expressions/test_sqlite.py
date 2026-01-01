from decimal import Decimal
from unittest import skipUnless

from django.db import connection
from django.db.models import DecimalField, Value
from django.db.models.sql import Query
from django.test import TestCase


class SQLiteDecimalExpressionsTests(TestCase):
    # Ensures the test only runs on SQLite.
    @skipUnless(connection.vendor == "sqlite", "SQLite-only test")
    def test_literal_value_decimal_cast_to_real(self):
        expr = Value(Decimal("3.0"), output_field=DecimalField())

        # We must use compiler.compile() so that Django looks for 'as_sqlite'
        compiler = connection.ops.compiler("SQLCompiler")(Query(None), connection, None)
        sql, params = compiler.compile(expr.resolve_expression(Query(None)))

        # Verify that the SQL is generated with CAST(... AS REAL)
        self.assertIn("CAST(", sql)
        self.assertIn("AS REAL)", sql)
        self.assertNotIn("AS NUMERIC", sql)
