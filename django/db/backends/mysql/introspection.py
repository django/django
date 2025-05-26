from collections import namedtuple

import sqlparse
from MySQLdb.constants import FIELD_TYPE

from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.backends.base.introspection import FieldInfo as BaseFieldInfo
from django.db.backends.base.introspection import TableInfo as BaseTableInfo
from django.db.models import Index
from django.utils.datastructures import OrderedSet

FieldInfo = namedtuple(
    "FieldInfo",
    [
        *BaseFieldInfo._fields,
        "extra",
        "is_unsigned",
        "has_json_constraint",
        "comment",
        "data_type",
    ],
)
InfoLine = namedtuple(
    "InfoLine",
    "col_name data_type max_len num_prec num_scale extra column_default "
    "collation is_unsigned comment",
)
TableInfo = namedtuple("TableInfo", [*BaseTableInfo._fields, "comment"])


class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        FIELD_TYPE.BLOB: "TextField",
        FIELD_TYPE.CHAR: "CharField",
        FIELD_TYPE.DECIMAL: "DecimalField",
        FIELD_TYPE.NEWDECIMAL: "DecimalField",
        FIELD_TYPE.DATE: "DateField",
        FIELD_TYPE.DATETIME: "DateTimeField",
        FIELD_TYPE.DOUBLE: "FloatField",
        FIELD_TYPE.FLOAT: "FloatField",
        FIELD_TYPE.INT24: "IntegerField",
        FIELD_TYPE.JSON: "JSONField",
        FIELD_TYPE.LONG: "IntegerField",
        FIELD_TYPE.LONGLONG: "BigIntegerField",
        FIELD_TYPE.SHORT: "SmallIntegerField",
        FIELD_TYPE.STRING: "CharField",
        FIELD_TYPE.TIME: "TimeField",
        FIELD_TYPE.TIMESTAMP: "DateTimeField",
        FIELD_TYPE.TINY: "IntegerField",
        FIELD_TYPE.TINY_BLOB: "TextField",
        FIELD_TYPE.MEDIUM_BLOB: "TextField",
        FIELD_TYPE.LONG_BLOB: "TextField",
        FIELD_TYPE.VAR_STRING: "CharField",
    }

    def get_field_type(self, data_type, description):
        field_type = super().get_field_type(data_type, description)
        if "auto_increment" in description.extra:
            if field_type == "IntegerField":
                return "AutoField"
            elif field_type == "BigIntegerField":
                return "BigAutoField"
            elif field_type == "SmallIntegerField":
                return "SmallAutoField"
        if description.is_unsigned:
            if field_type == "BigIntegerField":
                return "PositiveBigIntegerField"
            elif field_type == "IntegerField":
                return "PositiveIntegerField"
            elif field_type == "SmallIntegerField":
                return "PositiveSmallIntegerField"
        if description.data_type.upper() == "UUID":
            return "UUIDField"
        # JSON data type is an alias for LONGTEXT in MariaDB, use check
        # constraints clauses to introspect JSONField.
        if description.has_json_constraint:
            return "JSONField"
        return field_type

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute(
            """
            SELECT
                table_name,
                table_type,
                table_comment
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
        )
        return [
            TableInfo(row[0], {"BASE TABLE": "t", "VIEW": "v"}.get(row[1]), row[2])
            for row in cursor.fetchall()
        ]

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface."
        """
        json_constraints = {}
        if (
            self.connection.mysql_is_mariadb
            and self.connection.features.can_introspect_json_field
        ):
            # JSON data type is an alias for LONGTEXT in MariaDB, select
            # JSON_VALID() constraints to introspect JSONField.
            cursor.execute(
                """
                SELECT c.constraint_name AS column_name
                FROM information_schema.check_constraints AS c
                WHERE
                    c.table_name = %s AND
                    LOWER(c.check_clause) =
                        'json_valid(`' + LOWER(c.constraint_name) + '`)' AND
                    c.constraint_schema = DATABASE()
                """,
                [table_name],
            )
            json_constraints = {row[0] for row in cursor.fetchall()}
        # A default collation for the given table.
        cursor.execute(
            """
            SELECT  table_collation
            FROM    information_schema.tables
            WHERE   table_schema = DATABASE()
            AND     table_name = %s
            """,
            [table_name],
        )
        row = cursor.fetchone()
        default_column_collation = row[0] if row else ""
        # information_schema database gives more accurate results for some figures:
        # - varchar length returned by cursor.description is an internal length,
        #   not visible length (#5725)
        # - precision and scale (for decimal fields) (#5014)
        # - auto_increment is not available in cursor.description
        cursor.execute(
            """
            SELECT
                column_name, data_type, character_maximum_length,
                numeric_precision, numeric_scale, extra, column_default,
                CASE
                    WHEN collation_name = %s THEN NULL
                    ELSE collation_name
                END AS collation_name,
                CASE
                    WHEN column_type LIKE '%% unsigned' THEN 1
                    ELSE 0
                END AS is_unsigned,
                column_comment
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()
            """,
            [default_column_collation, table_name],
        )
        field_info = {line[0]: InfoLine(*line) for line in cursor.fetchall()}

        cursor.execute(
            "SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name)
        )

        def to_int(i):
            return int(i) if i is not None else i

        fields = []
        for line in cursor.description:
            info = field_info[line[0]]
            fields.append(
                FieldInfo(
                    *line[:2],
                    to_int(info.max_len) or line[2],
                    to_int(info.max_len) or line[3],
                    to_int(info.num_prec) or line[4],
                    to_int(info.num_scale) or line[5],
                    line[6],
                    info.column_default,
                    info.collation,
                    info.extra,
                    info.is_unsigned,
                    line[0] in json_constraints,
                    info.comment,
                    info.data_type,
                )
            )
        return fields

    def get_sequences(self, cursor, table_name, table_fields=()):
        for field_info in self.get_table_description(cursor, table_name):
            if "auto_increment" in field_info.extra:
                # MySQL allows only one auto-increment column per table.
                return [{"table": table_name, "column": field_info.name}]
        return []

    def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all foreign keys in the given table.
        """
        cursor.execute(
            """
            SELECT column_name, referenced_column_name, referenced_table_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL
            """,
            [table_name],
        )
        return {
            field_name: (other_field, other_table)
            for field_name, other_field, other_table in cursor.fetchall()
        }

    def get_storage_engine(self, cursor, table_name):
        """
        Retrieve the storage engine for a given table. Return the default
        storage engine if the table doesn't exist.
        """
        cursor.execute(
            """
            SELECT engine
            FROM information_schema.tables
            WHERE
                table_name = %s AND
                table_schema = DATABASE()
            """,
            [table_name],
        )
        result = cursor.fetchone()
        if not result:
            return self.connection.features._mysql_storage_engine
        return result[0]

    def _parse_constraint_columns(self, check_clause, columns):
        check_columns = OrderedSet()
        statement = sqlparse.parse(check_clause)[0]
        tokens = (token for token in statement.flatten() if not token.is_whitespace)
        for token in tokens:
            if (
                token.ttype == sqlparse.tokens.Name
                and self.connection.ops.quote_name(token.value) == token.value
                and token.value[1:-1] in columns
            ):
                check_columns.add(token.value[1:-1])
        return check_columns

    def get_constraints(self, cursor, table_name):
        """
        Retrieve any constraints or keys (unique, pk, fk, check, index) across
        one or more columns.
        """
        constraints = {}
        # Get the actual constraint names and columns
        name_query = """
            SELECT kc.`constraint_name`, kc.`column_name`,
                kc.`referenced_table_name`, kc.`referenced_column_name`,
                c.`constraint_type`
            FROM
                information_schema.key_column_usage AS kc,
                information_schema.table_constraints AS c
            WHERE
                kc.table_schema = DATABASE() AND
                (
                    kc.referenced_table_schema = DATABASE() OR
                    kc.referenced_table_schema IS NULL
                ) AND
                c.table_schema = kc.table_schema AND
                c.constraint_name = kc.constraint_name AND
                c.constraint_type != 'CHECK' AND
                kc.table_name = %s
            ORDER BY kc.`ordinal_position`
        """
        cursor.execute(name_query, [table_name])
        for constraint, column, ref_table, ref_column, kind in cursor.fetchall():
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": OrderedSet(),
                    "primary_key": kind == "PRIMARY KEY",
                    "unique": kind in {"PRIMARY KEY", "UNIQUE"},
                    "index": False,
                    "check": False,
                    "foreign_key": (ref_table, ref_column) if ref_column else None,
                }
                if self.connection.features.supports_index_column_ordering:
                    constraints[constraint]["orders"] = []
            constraints[constraint]["columns"].add(column)
        # Add check constraints.
        if self.connection.features.can_introspect_check_constraints:
            unnamed_constraints_index = 0
            columns = {
                info.name for info in self.get_table_description(cursor, table_name)
            }
            if self.connection.mysql_is_mariadb:
                type_query = """
                    SELECT c.constraint_name, c.check_clause
                    FROM information_schema.check_constraints AS c
                    WHERE
                        c.constraint_schema = DATABASE() AND
                        c.table_name = %s
                """
            else:
                type_query = """
                    SELECT cc.constraint_name, cc.check_clause
                    FROM
                        information_schema.check_constraints AS cc,
                        information_schema.table_constraints AS tc
                    WHERE
                        cc.constraint_schema = DATABASE() AND
                        tc.table_schema = cc.constraint_schema AND
                        cc.constraint_name = tc.constraint_name AND
                        tc.constraint_type = 'CHECK' AND
                        tc.table_name = %s
                """
            cursor.execute(type_query, [table_name])
            for constraint, check_clause in cursor.fetchall():
                constraint_columns = self._parse_constraint_columns(
                    check_clause, columns
                )
                # Ensure uniqueness of unnamed constraints. Unnamed unique
                # and check columns constraints have the same name as
                # a column.
                if set(constraint_columns) == {constraint}:
                    unnamed_constraints_index += 1
                    constraint = "__unnamed_constraint_%s__" % unnamed_constraints_index
                constraints[constraint] = {
                    "columns": constraint_columns,
                    "primary_key": False,
                    "unique": False,
                    "index": False,
                    "check": True,
                    "foreign_key": None,
                }
        # Now add in the indexes
        cursor.execute(
            "SHOW INDEX FROM %s" % self.connection.ops.quote_name(table_name)
        )
        for table, non_unique, index, colseq, column, order, type_ in [
            x[:6] + (x[10],) for x in cursor.fetchall()
        ]:
            if index not in constraints:
                constraints[index] = {
                    "columns": OrderedSet(),
                    "primary_key": False,
                    "unique": not non_unique,
                    "check": False,
                    "foreign_key": None,
                }
                if self.connection.features.supports_index_column_ordering:
                    constraints[index]["orders"] = []
            constraints[index]["index"] = True
            constraints[index]["type"] = (
                Index.suffix if type_ == "BTREE" else type_.lower()
            )
            constraints[index]["columns"].add(column)
            if self.connection.features.supports_index_column_ordering:
                constraints[index]["orders"].append("DESC" if order == "D" else "ASC")
        # Convert the sorted sets to lists
        for constraint in constraints.values():
            constraint["columns"] = list(constraint["columns"])
        return constraints
