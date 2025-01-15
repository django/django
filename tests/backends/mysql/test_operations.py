import unittest
from datetime import datetime

from django.core.management.color import no_style
from django.db import connection
from django.db.backends.oracle.operations import DatabaseOperations
from django.test import SimpleTestCase

from ..models import Person, Tag


@unittest.skipUnless(connection.vendor == "mysql", "MySQL tests.")
class MySQLOperationsTests(SimpleTestCase):
    def test_sql_flush(self):
        # allow_cascade doesn't change statements on MySQL.
        for allow_cascade in [False, True]:
            with self.subTest(allow_cascade=allow_cascade):
                self.assertEqual(
                    connection.ops.sql_flush(
                        no_style(),
                        [Person._meta.db_table, Tag._meta.db_table],
                        allow_cascade=allow_cascade,
                    ),
                    [
                        "SET FOREIGN_KEY_CHECKS = 0;",
                        "DELETE FROM `backends_person`;",
                        "DELETE FROM `backends_tag`;",
                        "SET FOREIGN_KEY_CHECKS = 1;",
                    ],
                )

    def test_sql_flush_sequences(self):
        # allow_cascade doesn't change statements on MySQL.
        for allow_cascade in [False, True]:
            with self.subTest(allow_cascade=allow_cascade):
                self.assertEqual(
                    connection.ops.sql_flush(
                        no_style(),
                        [Person._meta.db_table, Tag._meta.db_table],
                        reset_sequences=True,
                        allow_cascade=allow_cascade,
                    ),
                    [
                        "SET FOREIGN_KEY_CHECKS = 0;",
                        "TRUNCATE `backends_person`;",
                        "TRUNCATE `backends_tag`;",
                        "SET FOREIGN_KEY_CHECKS = 1;",
                    ],
                )

    def test_date_extract_sql(self):
        op = DatabaseOperations(connection=connection)

        # Test valid lookup types
        valid_lookups = [
            "year",
            "month",
            "day",
            "week_day",
            "iso_week_day",
            "week",
            "quarter",
            "iso_year",
            "hour",
            "minute",
            "second",
        ]
        for lookup in valid_lookups:
            with self.subTest(lookup=lookup):
                sql, params = op.date_extract_sql(lookup, "test_date")
                self.assertIn(lookup.upper(), sql)
                self.assertEqual(params, ())

        # Test invalid lookup type
        with self.assertRaisesMessage(
            ValueError, "Invalid lookup type: 'invalid_lookup'"
        ):
            op.date_extract_sql("invalid_lookup", "test_date")

        # Test that uppercase lookup types are accepted
        sql, params = op.date_extract_sql("YEAR", "test_date")
        self.assertIn("YEAR", sql)
        self.assertEqual(params, ())

        # Test that mixed case lookup types are not accepted
        with self.assertRaisesMessage(ValueError, "Invalid lookup type: 'YeAr'"):
            op.date_extract_sql("YeAr", "test_date")


class DatabaseOperationsTests(unittest.TestCase):
    def setUp(self):
        self.ops = DatabaseOperations(connection)

    def test_date_extract_sql(self):
        # Test for various lookup types
        test_cases = [
            ("year", "EXTRACT(YEAR FROM %s)", []),
            ("quarter", "EXTRACT(QUARTER FROM %s)", []),
            ("month", "EXTRACT(MONTH FROM %s)", []),
            ("week", "EXTRACT(WEEK FROM %s)", []),
            ("week_day", "DAYOFWEEK(%s)", []),
            ("iso_week_day", "DAYOFWEEK(%s)", []),
            ("day", "EXTRACT(DAY FROM %s)", []),
            ("hour", "EXTRACT(HOUR FROM %s)", []),
            ("minute", "EXTRACT(MINUTE FROM %s)", []),
            ("second", "EXTRACT(SECOND FROM %s)", []),
        ]

        for lookup_type, expected_sql, expected_params in test_cases:
            with self.subTest(lookup_type=lookup_type):
                sql, params = self.ops.date_extract_sql(lookup_type, "test_date")
                self.assertEqual(sql, expected_sql)
                self.assertEqual(params, expected_params)

    def test_date_extract_sql_invalid_lookup_type(self):
        with self.assertRaises(ValueError):
            self.ops.date_extract_sql("invalid", "test_date")

    def test_date_trunc_sql(self):
        # Test for various lookup types
        test_cases = [
            ("year", "DATE_TRUNC(%s, %%s)"),
            ("quarter", "DATE_TRUNC(%s, %%s)"),
            ("month", "DATE_TRUNC(%s, %%s)"),
            ("week", "DATE_TRUNC(%s, %%s)"),
            ("day", "DATE_TRUNC(%s, %%s)"),
            ("hour", "DATE_TRUNC(%s, %%s)"),
            ("minute", "DATE_TRUNC(%s, %%s)"),
            ("second", "DATE_TRUNC(%s, %%s)"),
        ]

        for lookup_type, expected_sql in test_cases:
            with self.subTest(lookup_type=lookup_type):
                sql = self.ops.date_trunc_sql(lookup_type, "test_date")
                self.assertEqual(sql, expected_sql % lookup_type)

    def test_date_trunc_sql_invalid_lookup_type(self):
        with self.assertRaises(ValueError):
            self.ops.date_trunc_sql("invalid", "test_date")

    def test_datetime_cast_date_sql(self):
        sql = self.ops.datetime_cast_date_sql("test_datetime", "test_tzname")
        self.assertEqual(sql, "CAST(%s AS DATE)")

    def test_datetime_cast_time_sql(self):
        sql = self.ops.datetime_cast_time_sql("test_datetime", "test_tzname")
        self.assertEqual(sql, "CAST(%s AS TIME)")

    def test_datetime_extract_sql(self):
        sql, params = self.ops.datetime_extract_sql(
            "hour", "test_datetime", "test_tzname"
        )
        self.assertEqual(sql, "EXTRACT(HOUR FROM %s)")
        self.assertEqual(params, [])

    def test_datetime_trunc_sql(self):
        sql = self.ops.datetime_trunc_sql("hour", "test_datetime", "test_tzname")
        self.assertEqual(sql, "DATE_TRUNC(%s, %%s)")
