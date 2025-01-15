import unittest
from datetime import datetime

from django.core.management.color import no_style
from django.db import connection
from django.db.backends.oracle.operations import DatabaseOperations
from django.test import TransactionTestCase

from ..models import Person, Tag


@unittest.skipUnless(connection.vendor == "oracle", "Oracle tests")
class OperationsTests(TransactionTestCase):
    available_apps = ["backends"]

    def setUp(self):
        self.ops = DatabaseOperations(connection=connection)

    def test_sequence_name_truncation(self):
        seq_name = connection.ops._get_no_autofield_sequence_name(
            "schema_authorwithevenlongee869"
        )
        self.assertEqual(seq_name, "SCHEMA_AUTHORWITHEVENLOB0B8_SQ")

    def test_bulk_batch_size(self):
        # Oracle restricts the number of parameters in a query.
        objects = range(2**16)
        self.assertEqual(connection.ops.bulk_batch_size([], objects), len(objects))
        # Each field is a parameter for each object.
        self.assertEqual(
            connection.ops.bulk_batch_size(["id"], objects),
            connection.features.max_query_params,
        )
        self.assertEqual(
            connection.ops.bulk_batch_size(["id", "other"], objects),
            connection.features.max_query_params // 2,
        )

    def test_sql_flush(self):
        statements = connection.ops.sql_flush(
            no_style(),
            [Person._meta.db_table, Tag._meta.db_table],
        )
        # The tables and constraints are processed in an unordered set.
        self.assertEqual(
            statements[0],
            'ALTER TABLE "BACKENDS_TAG" DISABLE CONSTRAINT '
            '"BACKENDS__CONTENT_T_FD9D7A85_F" KEEP INDEX;',
        )
        self.assertEqual(
            sorted(statements[1:-1]),
            [
                'TRUNCATE TABLE "BACKENDS_PERSON";',
                'TRUNCATE TABLE "BACKENDS_TAG";',
            ],
        )
        self.assertEqual(
            statements[-1],
            'ALTER TABLE "BACKENDS_TAG" ENABLE CONSTRAINT '
            '"BACKENDS__CONTENT_T_FD9D7A85_F";',
        )

    def test_sql_flush_allow_cascade(self):
        statements = connection.ops.sql_flush(
            no_style(),
            [Person._meta.db_table, Tag._meta.db_table],
            allow_cascade=True,
        )
        # The tables and constraints are processed in an unordered set.
        self.assertEqual(
            statements[0],
            'ALTER TABLE "BACKENDS_VERYLONGMODELNAME540F" DISABLE CONSTRAINT '
            '"BACKENDS__PERSON_ID_1DD5E829_F" KEEP INDEX;',
        )
        self.assertEqual(
            sorted(statements[1:-1]),
            [
                'TRUNCATE TABLE "BACKENDS_PERSON";',
                'TRUNCATE TABLE "BACKENDS_TAG";',
                'TRUNCATE TABLE "BACKENDS_VERYLONGMODELNAME540F";',
            ],
        )
        self.assertEqual(
            statements[-1],
            'ALTER TABLE "BACKENDS_VERYLONGMODELNAME540F" ENABLE CONSTRAINT '
            '"BACKENDS__PERSON_ID_1DD5E829_F";',
        )

    def test_sql_flush_sequences(self):
        statements = connection.ops.sql_flush(
            no_style(),
            [Person._meta.db_table, Tag._meta.db_table],
            reset_sequences=True,
        )
        # The tables and constraints are processed in an unordered set.
        self.assertEqual(
            statements[0],
            'ALTER TABLE "BACKENDS_TAG" DISABLE CONSTRAINT '
            '"BACKENDS__CONTENT_T_FD9D7A85_F" KEEP INDEX;',
        )
        self.assertEqual(
            sorted(statements[1:3]),
            [
                'TRUNCATE TABLE "BACKENDS_PERSON";',
                'TRUNCATE TABLE "BACKENDS_TAG";',
            ],
        )
        self.assertEqual(
            statements[3],
            'ALTER TABLE "BACKENDS_TAG" ENABLE CONSTRAINT '
            '"BACKENDS__CONTENT_T_FD9D7A85_F";',
        )
        # Sequences.
        self.assertEqual(len(statements[4:]), 2)
        self.assertIn("BACKENDS_PERSON_SQ", statements[4])
        self.assertIn("BACKENDS_TAG_SQ", statements[5])

    def test_sql_flush_sequences_allow_cascade(self):
        statements = connection.ops.sql_flush(
            no_style(),
            [Person._meta.db_table, Tag._meta.db_table],
            reset_sequences=True,
            allow_cascade=True,
        )
        # The tables and constraints are processed in an unordered set.
        self.assertEqual(
            statements[0],
            'ALTER TABLE "BACKENDS_VERYLONGMODELNAME540F" DISABLE CONSTRAINT '
            '"BACKENDS__PERSON_ID_1DD5E829_F" KEEP INDEX;',
        )
        self.assertEqual(
            sorted(statements[1:4]),
            [
                'TRUNCATE TABLE "BACKENDS_PERSON";',
                'TRUNCATE TABLE "BACKENDS_TAG";',
                'TRUNCATE TABLE "BACKENDS_VERYLONGMODELNAME540F";',
            ],
        )
        self.assertEqual(
            statements[4],
            'ALTER TABLE "BACKENDS_VERYLONGMODELNAME540F" ENABLE CONSTRAINT '
            '"BACKENDS__PERSON_ID_1DD5E829_F";',
        )
        # Sequences.
        self.assertEqual(len(statements[5:]), 3)
        self.assertIn("BACKENDS_PERSON_SQ", statements[5])
        self.assertIn("BACKENDS_VERYLONGMODELN7BE2_SQ", statements[6])
        self.assertIn("BACKENDS_TAG_SQ", statements[7])

    def test_date_extract_sql(self):
        # Test for various lookup types
        test_cases = [
            ("year", "TO_CHAR(test_date, %s)", ["YYYY"]),
            ("quarter", "TO_CHAR(test_date, %s)", ["Q"]),
            ("month", "TO_CHAR(test_date, %s)", ["MM"]),
            ("week", "TO_CHAR(test_date, %s)", ["IW"]),
            ("week_day", "TO_CHAR(test_date, %s)", ["D"]),
            ("iso_week_day", "TO_CHAR(test_date - 1, %s)", ["D"]),
            ("hour", "EXTRACT(HOUR FROM test_date)", []),
            ("minute", "EXTRACT(MINUTE FROM test_date)", []),
            ("second", "FLOOR(EXTRACT(SECOND FROM test_date))", []),
            ("iso_year", "TO_CHAR(test_date, %s)", ["IYYY"]),
        ]

        for lookup_type, expected_sql, expected_params in test_cases:
            with self.subTest(lookup_type=lookup_type):
                sql, params = self.ops.date_extract_sql(lookup_type, "test_date", [])
                self.assertEqual(sql, expected_sql)
                self.assertEqual(params, expected_params)

    def test_date_extract_sql_invalid_lookup_type(self):
        with self.assertRaises(ValueError):
            self.ops.date_extract_sql("invalid", "test_date", [])

    def test_date_extract_sql_with_timezone(self):
        # Test that the method works correctly when a timezone is involved
        sql, params = self.ops.date_extract_sql("hour", "test_date", ["UTC"])
        self.assertEqual(sql, "EXTRACT(HOUR FROM test_date)")
        self.assertEqual(params, ["UTC"])

    def test_date_extract_sql_params_passing(self):
        # Test that additional parameters are correctly passed through
        sql, params = self.ops.date_extract_sql(
            "year", "test_date", ["param1", "param2"]
        )
        self.assertEqual(sql, "TO_CHAR(test_date, %s)")
        self.assertEqual(params, ["param1", "param2", "YYYY"])
