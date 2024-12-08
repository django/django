from unittest import skipUnless

from django.db import connection, connections
from django.test import TestCase


@skipUnless(connection.vendor == "mysql", "MySQL tests")
class ParsingTests(TestCase):
    def test_parse_constraint_columns(self):
        _parse_constraint_columns = connection.introspection._parse_constraint_columns
        tests = (
            ("`height` >= 0", ["height"], ["height"]),
            ("`cost` BETWEEN 1 AND 10", ["cost"], ["cost"]),
            ("`ref1` > `ref2`", ["id", "ref1", "ref2"], ["ref1", "ref2"]),
            (
                "`start` IS NULL OR `end` IS NULL OR `start` < `end`",
                ["id", "start", "end"],
                ["start", "end"],
            ),
            ("JSON_VALID(`json_field`)", ["json_field"], ["json_field"]),
            ("CHAR_LENGTH(`name`) > 2", ["name"], ["name"]),
            ("lower(`ref1`) != 'test'", ["id", "owe", "ref1"], ["ref1"]),
            ("lower(`ref1`) != 'test'", ["id", "lower", "ref1"], ["ref1"]),
            ("`name` LIKE 'test%'", ["name"], ["name"]),
        )
        for check_clause, table_columns, expected_columns in tests:
            with self.subTest(check_clause):
                check_columns = _parse_constraint_columns(check_clause, table_columns)
                self.assertEqual(list(check_columns), expected_columns)


@skipUnless(connection.vendor == "mysql", "MySQL tests")
class StorageEngineTests(TestCase):
    databases = {"default", "other"}

    def test_get_storage_engine(self):
        table_name = "test_storage_engine"
        create_sql = "CREATE TABLE %s (id INTEGER) ENGINE = %%s" % table_name
        drop_sql = "DROP TABLE %s" % table_name
        default_connection = connections["default"]
        other_connection = connections["other"]
        try:
            with default_connection.cursor() as cursor:
                cursor.execute(create_sql % "InnoDB")
                self.assertEqual(
                    default_connection.introspection.get_storage_engine(
                        cursor, table_name
                    ),
                    "InnoDB",
                )
            with other_connection.cursor() as cursor:
                cursor.execute(create_sql % "MyISAM")
                self.assertEqual(
                    other_connection.introspection.get_storage_engine(
                        cursor, table_name
                    ),
                    "MyISAM",
                )
        finally:
            with default_connection.cursor() as cursor:
                cursor.execute(drop_sql)
            with other_connection.cursor() as cursor:
                cursor.execute(drop_sql)


@skipUnless(connection.vendor == "mysql", "MySQL specific SQL")
class TestCrossDatabaseRelations(TestCase):
    databases = {"default", "other"}

    def test_omit_cross_database_relations(self):
        default_connection = connections["default"]
        other_connection = connections["other"]
        main_table = "cross_schema_get_relations_main_table"
        main_table_quoted = default_connection.ops.quote_name(main_table)
        other_schema_quoted = other_connection.ops.quote_name(
            other_connection.settings_dict["NAME"]
        )
        rel_table = "cross_schema_get_relations_rel_table"
        rel_table_quoted = other_connection.ops.quote_name(rel_table)
        rel_column = "cross_schema_get_relations_rel_table_id"
        rel_column_quoted = other_connection.ops.quote_name(rel_column)
        try:
            with other_connection.cursor() as other_cursor:
                other_cursor.execute(
                    f"""
                    CREATE TABLE {rel_table_quoted} (
                        id integer AUTO_INCREMENT,
                        PRIMARY KEY (id)
                    )
                    """
                )
            with default_connection.cursor() as default_cursor:
                # Create table in the default schema with a cross-database
                # relation.
                default_cursor.execute(
                    f"""
                    CREATE TABLE {main_table_quoted} (
                        id integer AUTO_INCREMENT,
                        {rel_column_quoted} integer NOT NULL,
                        PRIMARY KEY (id),
                        FOREIGN KEY ({rel_column_quoted})
                        REFERENCES {other_schema_quoted}.{rel_table_quoted}(id)
                    )
                    """
                )
                relations = default_connection.introspection.get_relations(
                    default_cursor, main_table
                )
                constraints = default_connection.introspection.get_constraints(
                    default_cursor, main_table
                )
            self.assertEqual(len(relations), 0)
            rel_column_fk_constraints = [
                spec
                for name, spec in constraints.items()
                if spec["columns"] == [rel_column] and spec["foreign_key"] is not None
            ]
            self.assertEqual(len(rel_column_fk_constraints), 0)
        finally:
            with default_connection.cursor() as default_cursor:
                default_cursor.execute(f"DROP TABLE IF EXISTS {main_table_quoted}")
            with other_connection.cursor() as other_cursor:
                other_cursor.execute(f"DROP TABLE IF EXISTS {rel_table_quoted}")
