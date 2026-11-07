"""
Database introspection for DuckDB backend.
"""

from collections import namedtuple

from django.db import DatabaseError
from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.backends.base.introspection import FieldInfo as BaseFieldInfo
from django.db.backends.base.introspection import TableInfo
from django.db.models import Index

FieldInfo = namedtuple(
    "FieldInfo", [*BaseFieldInfo._fields, "pk", "has_json_constraint"]
)


class FlexibleFieldLookupDict:
    """Maps DuckDB SQL types to Django Field types."""
    base_data_types_reverse = {
        "BOOLEAN": "BooleanField",
        "TINYINT": "SmallIntegerField",
        "UTINYINT": "PositiveSmallIntegerField",
        "SMALLINT": "SmallIntegerField",
        "USMALLINT": "PositiveSmallIntegerField",
        "INTEGER": "IntegerField",
        "UINT": "PositiveIntegerField",
        "BIGINT": "BigIntegerField",
        "UBIGINT": "PositiveBigIntegerField",
        "HUGEINT": "BigIntegerField",
        "FLOAT": "FloatField",
        "DOUBLE": "FloatField",
        "DECIMAL": "DecimalField",
        "VARCHAR": "CharField",
        "TEXT": "TextField",
        "BLOB": "BinaryField",
        "DATE": "DateField",
        "TIMESTAMP": "DateTimeField",
        "TIMESTAMP_S": "DateTimeField",
        "TIMESTAMP_MS": "DateTimeField",
        "TIMESTAMP_NS": "DateTimeField",
        "TIME": "TimeField",
        "JSON": "JSONField",
        "UUID": "UUIDField",
    }

    def __getitem__(self, key):
        key = key.upper().split("(", 1)[0].strip()
        return self.base_data_types_reverse[key]


class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = FlexibleFieldLookupDict()

    def get_field_type(self, data_type, description):
        field_type = super().get_field_type(data_type, description)
        if description.pk and field_type in {
            "BigIntegerField",
            "IntegerField",
            "SmallIntegerField",
        }:
            return "AutoField"
        if description.has_json_constraint:
            return "JSONField"
        return field_type

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
            ORDER BY table_name
        """)
        result = []
        for row in cursor.fetchall():
            table_name = row[0]
            table_type = row[1]
            # table_type is 'BASE TABLE' or 'VIEW'
            if table_type == "VIEW":
                result.append(TableInfo(table_name, "v"))
            else:
                result.append(TableInfo(table_name, "t"))
        return result

    def get_table_description(self, cursor, table_name):
        """Return a description of the table with the DB-API cursor.description interface."""
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = ? AND table_schema = 'main'
            ORDER BY ordinal_position
        """, [table_name])
        columns = cursor.fetchall()
        if not columns:
            raise DatabaseError(f"Table {table_name} does not exist (empty pragma).")

        # Get primary key columns
        pk_columns = self.get_primary_key_columns(cursor, table_name)

        table_description = []
        for column in columns:
            name = column[0]
            data_type = column[1]
            is_nullable = column[2] == "YES"
            default = column[3]

            # Extract size from data_type if present (e.g., VARCHAR(100))
            size = None
            if "(" in data_type:
                try:
                    size = int(data_type.split("(")[1].split(")")[0])
                except (ValueError, IndexError):
                    pass

            table_description.append(
                FieldInfo(
                    name,
                    data_type,
                    size,
                    None,  # display_size
                    None,  # internal_size
                    None,  # precision
                    is_nullable,
                    default,
                    None,  # collation
                    name in pk_columns,
                    data_type.upper() == "JSON",
                )
            )
        return table_description

    def get_sequences(self, cursor, table_name, table_fields=()):
        # DuckDB doesn't have sequences
        return []

    def get_relations(self, cursor, table_name):
        """Return a dictionary of foreign key relations."""
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.update_rule,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON tc.constraint_name = rc.constraint_name
                AND tc.table_schema = rc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = ?
                AND tc.table_schema = 'main'
        """, [table_name])

        relations = {}
        for row in cursor.fetchall():
            column_name = row[1]
            ref_table_name = row[2]
            ref_column_name = row[3]
            on_delete = row[5]
            db_on_delete = self.on_delete_types.get(on_delete)
            relations[column_name] = (ref_column_name, ref_table_name, db_on_delete)
        return relations

    def get_primary_key_columns(self, cursor, table_name):
        cursor.execute("""
            SELECT column_name
            FROM information_schema.key_column_usage
            WHERE table_name = ? AND table_schema = 'main'
        """, [table_name])
        return [row[0] for row in cursor.fetchall()]

    def get_constraints(self, cursor, table_name):
        """Retrieve constraints and keys for a table."""
        constraints = {}

        # Get all constraints from information_schema
        cursor.execute("""
            SELECT
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_name = ? AND tc.table_schema = 'main'
            ORDER BY tc.constraint_type, tc.constraint_name
        """, [table_name])

        constraint_rows = cursor.fetchall()

        # Group constraints by name
        constraint_map = {}
        for row in constraint_rows:
            name = row[0]
            constraint_type = row[1]
            column = row[2]
            if name not in constraint_map:
                constraint_map[name] = {
                    "type": constraint_type,
                    "columns": [],
                }
            constraint_map[name]["columns"].append(column)

        # Get foreign key details
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = ?
                AND tc.table_schema = 'main'
        """, [table_name])

        fk_map = {}
        for row in cursor.fetchall():
            fk_map[row[0]] = (row[2], row[3])

        # Build constraints dict
        for name, info in constraint_map.items():
            constraint_type = info["type"]
            if constraint_type == "PRIMARY KEY":
                constraints["__primary__"] = {
                    "columns": info["columns"],
                    "primary_key": True,
                    "unique": False,
                    "foreign_key": None,
                    "check": False,
                    "index": False,
                }
            elif constraint_type == "UNIQUE":
                constraints[name] = {
                    "columns": info["columns"],
                    "primary_key": False,
                    "unique": True,
                    "foreign_key": None,
                    "check": False,
                    "index": False,
                }
            elif constraint_type == "FOREIGN KEY":
                ref = fk_map.get(name)
                if ref:
                    constraints[name] = {
                        "columns": info["columns"],
                        "primary_key": False,
                        "unique": False,
                        "foreign_key": (ref[0], ref[1]),
                        "check": False,
                        "index": False,
                    }
            elif constraint_type == "CHECK":
                constraints[name] = {
                    "columns": info["columns"],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": True,
                    "index": False,
                }

        # Get indexes
        cursor.execute("""
            SELECT index_name, tablename, index_columns
            FROM duckdb_indexes()
            WHERE schemaname = 'main' AND tablename = ?
        """, [table_name])

        for row in cursor.fetchall():
            index_name = row[0]
            # Skip primary key indexes
            if index_name.endswith("_pkey"):
                continue
            columns = row[2]
            if isinstance(columns, str):
                columns = [c.strip("[]'\" ") for c in columns.strip("[]").split(",")]
            constraints[index_name] = {
                "columns": columns,
                "primary_key": False,
                "unique": False,
                "foreign_key": None,
                "check": False,
                "index": True,
                "type": Index.suffix,
            }

        return constraints
