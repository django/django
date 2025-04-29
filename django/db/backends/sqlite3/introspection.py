from collections import namedtuple

import sqlparse

from django.db import DatabaseError
from django.db.backends.base.introspection import BaseDatabaseIntrospection
from django.db.backends.base.introspection import FieldInfo as BaseFieldInfo
from django.db.backends.base.introspection import TableInfo
from django.db.models import Index
from django.utils.regex_helper import _lazy_re_compile

FieldInfo = namedtuple(
    "FieldInfo", BaseFieldInfo._fields + ("pk", "has_json_constraint")
)

field_size_re = _lazy_re_compile(r"^\s*(?:var)?char\s*\(\s*(\d+)\s*\)\s*$")


def get_field_size(name):
    """Extract the size number from a "varchar(11)" type name"""
    m = field_size_re.search(name)
    return int(m[1]) if m else None


# This light wrapper "fakes" a dictionary interface, because some SQLite data
# types include variables in them -- e.g. "varchar(30)" -- and can't be matched
# as a simple dictionary lookup.
class FlexibleFieldLookupDict:
    # Maps SQL types to Django Field types. Some of the SQL types have multiple
    # entries here because SQLite allows for anything and doesn't normalize the
    # field type; it uses whatever was given.
    base_data_types_reverse = {
        "bool": "BooleanField",
        "boolean": "BooleanField",
        "smallint": "SmallIntegerField",
        "smallint unsigned": "PositiveSmallIntegerField",
        "smallinteger": "SmallIntegerField",
        "int": "IntegerField",
        "integer": "IntegerField",
        "bigint": "BigIntegerField",
        "integer unsigned": "PositiveIntegerField",
        "bigint unsigned": "PositiveBigIntegerField",
        "decimal": "DecimalField",
        "real": "FloatField",
        "text": "TextField",
        "char": "CharField",
        "varchar": "CharField",
        "blob": "BinaryField",
        "date": "DateField",
        "datetime": "DateTimeField",
        "time": "TimeField",
    }

    def __getitem__(self, key):
        key = key.lower().split("(", 1)[0].strip()
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
            # No support for BigAutoField or SmallAutoField as SQLite treats
            # all integer primary keys as signed 64-bit integers.
            return "AutoField"
        if description.has_json_constraint:
            return "JSONField"
        return field_type

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        # Skip the sqlite_sequence system table used for autoincrement key
        # generation.
        cursor.execute(
            """
            SELECT name, type FROM sqlite_master
            WHERE type in ('table', 'view') AND NOT name='sqlite_sequence'
            ORDER BY name"""
        )
        return [TableInfo(row[0], row[1][0]) for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        cursor.execute(
            "PRAGMA table_xinfo(%s)" % self.connection.ops.quote_name(table_name)
        )
        table_info = cursor.fetchall()
        if not table_info:
            raise DatabaseError(f"Table {table_name} does not exist (empty pragma).")
        collations = self._get_column_collations(cursor, table_name)
        json_columns = set()
        if self.connection.features.can_introspect_json_field:
            for line in table_info:
                column = line[1]
                json_constraint_sql = '%%json_valid("%s")%%' % column
                has_json_constraint = cursor.execute(
                    """
                    SELECT sql
                    FROM sqlite_master
                    WHERE
                        type = 'table' AND
                        name = %s AND
                        sql LIKE %s
                """,
                    [table_name, json_constraint_sql],
                ).fetchone()
                if has_json_constraint:
                    json_columns.add(column)
        table_description = [
            FieldInfo(
                name,
                data_type,
                get_field_size(data_type),
                None,
                None,
                None,
                not notnull,
                default,
                collations.get(name),
                bool(pk),
                name in json_columns,
            )
            for cid, name, data_type, notnull, default, pk, hidden in table_info
            if hidden
            in [
                0,  # Normal column.
                2,  # Virtual generated column.
                3,  # Stored generated column.
            ]
        ]
        # If the primary key is composed of multiple columns they should not
        # be individually marked as pk.
        primary_key = [
            index for index, field_info in enumerate(table_description) if field_info.pk
        ]
        if len(primary_key) > 1:
            for index in primary_key:
                table_description[index] = table_description[index]._replace(pk=False)
        return table_description

    def get_sequences(self, cursor, table_name, table_fields=()):
        pk_col = self.get_primary_key_column(cursor, table_name)
        return [{"table": table_name, "column": pk_col}]

    def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {column_name: (ref_column_name, ref_table_name)}
        representing all foreign keys in the given table.
        """
        cursor.execute(
            "PRAGMA foreign_key_list(%s)" % self.connection.ops.quote_name(table_name)
        )
        return {
            column_name: (ref_column_name, ref_table_name)
            for (
                _,
                _,
                ref_table_name,
                column_name,
                ref_column_name,
                *_,
            ) in cursor.fetchall()
        }

    def get_primary_key_columns(self, cursor, table_name):
        cursor.execute(
            "PRAGMA table_info(%s)" % self.connection.ops.quote_name(table_name)
        )
        return [name for _, name, *_, pk in cursor.fetchall() if pk]

    def _parse_column_or_constraint_definition(self, tokens, columns):
        token = None
        is_constraint_definition = None
        field_name = None
        constraint_name = None
        unique = False
        unique_columns = []
        check = False
        check_columns = []
        braces_deep = 0
        for token in tokens:
            if token.match(sqlparse.tokens.Punctuation, "("):
                braces_deep += 1
            elif token.match(sqlparse.tokens.Punctuation, ")"):
                braces_deep -= 1
                if braces_deep < 0:
                    # End of columns and constraints for table definition.
                    break
            elif braces_deep == 0 and token.match(sqlparse.tokens.Punctuation, ","):
                # End of current column or constraint definition.
                break
            # Detect column or constraint definition by first token.
            if is_constraint_definition is None:
                is_constraint_definition = token.match(
                    sqlparse.tokens.Keyword, "CONSTRAINT"
                )
                if is_constraint_definition:
                    continue
            if is_constraint_definition:
                # Detect constraint name by second token.
                if constraint_name is None:
                    if token.ttype in (sqlparse.tokens.Name, sqlparse.tokens.Keyword):
                        constraint_name = token.value
                    elif token.ttype == sqlparse.tokens.Literal.String.Symbol:
                        constraint_name = token.value[1:-1]
                # Start constraint columns parsing after UNIQUE keyword.
                if token.match(sqlparse.tokens.Keyword, "UNIQUE"):
                    unique = True
                    unique_braces_deep = braces_deep
                elif unique:
                    if unique_braces_deep == braces_deep:
                        if unique_columns:
                            # Stop constraint parsing.
                            unique = False
                        continue
                    if token.ttype in (sqlparse.tokens.Name, sqlparse.tokens.Keyword):
                        unique_columns.append(token.value)
                    elif token.ttype == sqlparse.tokens.Literal.String.Symbol:
                        unique_columns.append(token.value[1:-1])
            else:
                # Detect field name by first token.
                if field_name is None:
                    if token.ttype in (sqlparse.tokens.Name, sqlparse.tokens.Keyword):
                        field_name = token.value
                    elif token.ttype == sqlparse.tokens.Literal.String.Symbol:
                        field_name = token.value[1:-1]
                if token.match(sqlparse.tokens.Keyword, "UNIQUE"):
                    unique_columns = [field_name]
            # Start constraint columns parsing after CHECK keyword.
            if token.match(sqlparse.tokens.Keyword, "CHECK"):
                check = True
                check_braces_deep = braces_deep
            elif check:
                if check_braces_deep == braces_deep:
                    if check_columns:
                        # Stop constraint parsing.
                        check = False
                    continue
                if token.ttype in (sqlparse.tokens.Name, sqlparse.tokens.Keyword):
                    if token.value in columns:
                        check_columns.append(token.value)
                elif token.ttype == sqlparse.tokens.Literal.String.Symbol:
                    if token.value[1:-1] in columns:
                        check_columns.append(token.value[1:-1])
        unique_constraint = (
            {
                "unique": True,
                "columns": unique_columns,
                "primary_key": False,
                "foreign_key": None,
                "check": False,
                "index": False,
            }
            if unique_columns
            else None
        )
        check_constraint = (
            {
                "check": True,
                "columns": check_columns,
                "primary_key": False,
                "unique": False,
                "foreign_key": None,
                "index": False,
            }
            if check_columns
            else None
        )
        return constraint_name, unique_constraint, check_constraint, token

    def _parse_table_constraints(self, sql, columns):
        # Check constraint parsing is based of SQLite syntax diagram.
        # https://www.sqlite.org/syntaxdiagrams.html#table-constraint
        statement = sqlparse.parse(sql)[0]
        constraints = {}
        unnamed_constrains_index = 0
        tokens = (token for token in statement.flatten() if not token.is_whitespace)
        # Go to columns and constraint definition
        for token in tokens:
            if token.match(sqlparse.tokens.Punctuation, "("):
                break
        # Parse columns and constraint definition
        while True:
            (
                constraint_name,
                unique,
                check,
                end_token,
            ) = self._parse_column_or_constraint_definition(tokens, columns)
            if unique:
                if constraint_name:
                    constraints[constraint_name] = unique
                else:
                    unnamed_constrains_index += 1
                    constraints[
                        "__unnamed_constraint_%s__" % unnamed_constrains_index
                    ] = unique
            if check:
                if constraint_name:
                    constraints[constraint_name] = check
                else:
                    unnamed_constrains_index += 1
                    constraints[
                        "__unnamed_constraint_%s__" % unnamed_constrains_index
                    ] = check
            if end_token.match(sqlparse.tokens.Punctuation, ")"):
                break
        return constraints

    def get_constraints(self, cursor, table_name):
        """
        Retrieve any constraints or keys (unique, pk, fk, check, index) across
        one or more columns.
        """
        constraints = {}
        # Find inline check constraints.
        try:
            table_schema = cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' and name=%s",
                [table_name],
            ).fetchone()[0]
        except TypeError:
            # table_name is a view.
            pass
        else:
            columns = {
                info.name for info in self.get_table_description(cursor, table_name)
            }
            constraints.update(self._parse_table_constraints(table_schema, columns))

        # Get the index info
        cursor.execute(
            "PRAGMA index_list(%s)" % self.connection.ops.quote_name(table_name)
        )
        for row in cursor.fetchall():
            # SQLite 3.8.9+ has 5 columns, however older versions only give 3
            # columns. Discard last 2 columns if there.
            number, index, unique = row[:3]
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name=%s",
                [index],
            )
            # There's at most one row.
            (sql,) = cursor.fetchone() or (None,)
            # Inline constraints are already detected in
            # _parse_table_constraints(). The reasons to avoid fetching inline
            # constraints from `PRAGMA index_list` are:
            # - Inline constraints can have a different name and information
            #   than what `PRAGMA index_list` gives.
            # - Not all inline constraints may appear in `PRAGMA index_list`.
            if not sql:
                # An inline constraint
                continue
            # Get the index info for that index
            cursor.execute(
                "PRAGMA index_info(%s)" % self.connection.ops.quote_name(index)
            )
            for index_rank, column_rank, column in cursor.fetchall():
                if index not in constraints:
                    constraints[index] = {
                        "columns": [],
                        "primary_key": False,
                        "unique": bool(unique),
                        "foreign_key": None,
                        "check": False,
                        "index": True,
                    }
                constraints[index]["columns"].append(column)
            # Add type and column orders for indexes
            if constraints[index]["index"]:
                # SQLite doesn't support any index type other than b-tree
                constraints[index]["type"] = Index.suffix
                orders = self._get_index_columns_orders(sql)
                if orders is not None:
                    constraints[index]["orders"] = orders
        # Get the PK
        pk_columns = self.get_primary_key_columns(cursor, table_name)
        if pk_columns:
            # SQLite doesn't actually give a name to the PK constraint,
            # so we invent one. This is fine, as the SQLite backend never
            # deletes PK constraints by name, as you can't delete constraints
            # in SQLite; we remake the table with a new PK instead.
            constraints["__primary__"] = {
                "columns": pk_columns,
                "primary_key": True,
                "unique": False,  # It's not actually a unique constraint.
                "foreign_key": None,
                "check": False,
                "index": False,
            }
        relations = enumerate(self.get_relations(cursor, table_name).items())
        constraints.update(
            {
                f"fk_{index}": {
                    "columns": [column_name],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": (ref_table_name, ref_column_name),
                    "check": False,
                    "index": False,
                }
                for index, (column_name, (ref_column_name, ref_table_name)) in relations
            }
        )
        return constraints

    def _get_index_columns_orders(self, sql):
        tokens = sqlparse.parse(sql)[0]
        for token in tokens:
            if isinstance(token, sqlparse.sql.Parenthesis):
                columns = str(token).strip("()").split(", ")
                return ["DESC" if info.endswith("DESC") else "ASC" for info in columns]
        return None

    def _get_column_collations(self, cursor, table_name):
        row = cursor.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = %s
        """,
            [table_name],
        ).fetchone()
        if not row:
            return {}

        sql = row[0]
        columns = str(sqlparse.parse(sql)[0][-1]).strip("()").split(", ")
        collations = {}
        for column in columns:
            tokens = column[1:].split()
            column_name = tokens[0].strip('"')
            for index, token in enumerate(tokens):
                if token == "COLLATE":
                    collation = tokens[index + 1]
                    break
            else:
                collation = None
            collations[column_name] = collation
        return collations
