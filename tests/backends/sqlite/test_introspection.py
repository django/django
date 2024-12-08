import unittest

import sqlparse

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == "sqlite", "SQLite tests")
class IntrospectionTests(TestCase):
    def test_get_primary_key_column(self):
        """
        Get the primary key column regardless of whether or not it has
        quotation.
        """
        testable_column_strings = (
            ("id", "id"),
            ("[id]", "id"),
            ("`id`", "id"),
            ('"id"', "id"),
            ("[id col]", "id col"),
            ("`id col`", "id col"),
            ('"id col"', "id col"),
        )
        with connection.cursor() as cursor:
            for column, expected_string in testable_column_strings:
                sql = "CREATE TABLE test_primary (%s int PRIMARY KEY NOT NULL)" % column
                with self.subTest(column=column):
                    try:
                        cursor.execute(sql)
                        field = connection.introspection.get_primary_key_column(
                            cursor, "test_primary"
                        )
                        self.assertEqual(field, expected_string)
                    finally:
                        cursor.execute("DROP TABLE test_primary")

    def test_get_primary_key_column_pk_constraint(self):
        sql = """
            CREATE TABLE test_primary(
                id INTEGER NOT NULL,
                created DATE,
                PRIMARY KEY(id)
            )
        """
        with connection.cursor() as cursor:
            try:
                cursor.execute(sql)
                field = connection.introspection.get_primary_key_column(
                    cursor,
                    "test_primary",
                )
                self.assertEqual(field, "id")
            finally:
                cursor.execute("DROP TABLE test_primary")


@unittest.skipUnless(connection.vendor == "sqlite", "SQLite tests")
class ParsingTests(TestCase):
    def parse_definition(self, sql, columns):
        """Parse a column or constraint definition."""
        statement = sqlparse.parse(sql)[0]
        tokens = (token for token in statement.flatten() if not token.is_whitespace)
        with connection.cursor():
            return connection.introspection._parse_column_or_constraint_definition(
                tokens, set(columns)
            )

    def assertConstraint(self, constraint_details, cols, unique=False, check=False):
        self.assertEqual(
            constraint_details,
            {
                "unique": unique,
                "columns": cols,
                "primary_key": False,
                "foreign_key": None,
                "check": check,
                "index": False,
            },
        )

    def test_unique_column(self):
        tests = (
            ('"ref" integer UNIQUE,', ["ref"]),
            ("ref integer UNIQUE,", ["ref"]),
            ('"customname" integer UNIQUE,', ["customname"]),
            ("customname integer UNIQUE,", ["customname"]),
        )
        for sql, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertIsNone(constraint)
                self.assertConstraint(details, columns, unique=True)
                self.assertIsNone(check)

    def test_unique_constraint(self):
        tests = (
            ('CONSTRAINT "ref" UNIQUE ("ref"),', "ref", ["ref"]),
            ("CONSTRAINT ref UNIQUE (ref),", "ref", ["ref"]),
            (
                'CONSTRAINT "customname1" UNIQUE ("customname2"),',
                "customname1",
                ["customname2"],
            ),
            (
                "CONSTRAINT customname1 UNIQUE (customname2),",
                "customname1",
                ["customname2"],
            ),
        )
        for sql, constraint_name, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertEqual(constraint, constraint_name)
                self.assertConstraint(details, columns, unique=True)
                self.assertIsNone(check)

    def test_unique_constraint_multicolumn(self):
        tests = (
            (
                'CONSTRAINT "ref" UNIQUE ("ref", "customname"),',
                "ref",
                ["ref", "customname"],
            ),
            ("CONSTRAINT ref UNIQUE (ref, customname),", "ref", ["ref", "customname"]),
        )
        for sql, constraint_name, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertEqual(constraint, constraint_name)
                self.assertConstraint(details, columns, unique=True)
                self.assertIsNone(check)

    def test_check_column(self):
        tests = (
            ('"ref" varchar(255) CHECK ("ref" != \'test\'),', ["ref"]),
            ("ref varchar(255) CHECK (ref != 'test'),", ["ref"]),
            (
                '"customname1" varchar(255) CHECK ("customname2" != \'test\'),',
                ["customname2"],
            ),
            (
                "customname1 varchar(255) CHECK (customname2 != 'test'),",
                ["customname2"],
            ),
        )
        for sql, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertIsNone(constraint)
                self.assertIsNone(details)
                self.assertConstraint(check, columns, check=True)

    def test_check_constraint(self):
        tests = (
            ('CONSTRAINT "ref" CHECK ("ref" != \'test\'),', "ref", ["ref"]),
            ("CONSTRAINT ref CHECK (ref != 'test'),", "ref", ["ref"]),
            (
                'CONSTRAINT "customname1" CHECK ("customname2" != \'test\'),',
                "customname1",
                ["customname2"],
            ),
            (
                "CONSTRAINT customname1 CHECK (customname2 != 'test'),",
                "customname1",
                ["customname2"],
            ),
        )
        for sql, constraint_name, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertEqual(constraint, constraint_name)
                self.assertIsNone(details)
                self.assertConstraint(check, columns, check=True)

    def test_check_column_with_operators_and_functions(self):
        tests = (
            ('"ref" integer CHECK ("ref" BETWEEN 1 AND 10),', ["ref"]),
            ('"ref" varchar(255) CHECK ("ref" LIKE \'test%\'),', ["ref"]),
            (
                '"ref" varchar(255) CHECK (LENGTH(ref) > "max_length"),',
                ["ref", "max_length"],
            ),
        )
        for sql, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertIsNone(constraint)
                self.assertIsNone(details)
                self.assertConstraint(check, columns, check=True)

    def test_check_and_unique_column(self):
        tests = (
            ('"ref" varchar(255) CHECK ("ref" != \'test\') UNIQUE,', ["ref"]),
            ("ref varchar(255) UNIQUE CHECK (ref != 'test'),", ["ref"]),
        )
        for sql, columns in tests:
            with self.subTest(sql=sql):
                constraint, details, check, _ = self.parse_definition(sql, columns)
                self.assertIsNone(constraint)
                self.assertConstraint(details, columns, unique=True)
                self.assertConstraint(check, columns, check=True)
