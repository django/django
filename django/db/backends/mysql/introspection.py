from collections import namedtuple

import sqlparse
from MySQLdb.constants import FIELD_TYPE

from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo as BaseFieldInfo, TableInfo,
)
from django.db.models.indexes import Index
from django.utils.datastructures import OrderedSet

FieldInfo = namedtuple('FieldInfo', BaseFieldInfo._fields + ('extra', 'is_unsigned'))
InfoLine = namedtuple('InfoLine', 'col_name data_type max_len num_prec num_scale extra column_default is_unsigned')


class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        FIELD_TYPE.BLOB: 'TextField',
        FIELD_TYPE.CHAR: 'CharField',
        FIELD_TYPE.DECIMAL: 'DecimalField',
        FIELD_TYPE.NEWDECIMAL: 'DecimalField',
        FIELD_TYPE.DATE: 'DateField',
        FIELD_TYPE.DATETIME: 'DateTimeField',
        FIELD_TYPE.DOUBLE: 'FloatField',
        FIELD_TYPE.FLOAT: 'FloatField',
        FIELD_TYPE.INT24: 'IntegerField',
        FIELD_TYPE.LONG: 'IntegerField',
        FIELD_TYPE.LONGLONG: 'BigIntegerField',
        FIELD_TYPE.SHORT: 'SmallIntegerField',
        FIELD_TYPE.STRING: 'CharField',
        FIELD_TYPE.TIME: 'TimeField',
        FIELD_TYPE.TIMESTAMP: 'DateTimeField',
        FIELD_TYPE.TINY: 'IntegerField',
        FIELD_TYPE.TINY_BLOB: 'TextField',
        FIELD_TYPE.MEDIUM_BLOB: 'TextField',
        FIELD_TYPE.LONG_BLOB: 'TextField',
        FIELD_TYPE.VAR_STRING: 'CharField',
    }

    def get_field_type(self, data_type, description):
        field_type = super().get_field_type(data_type, description)
        if 'auto_increment' in description.extra:
            if field_type == 'IntegerField':
                return 'AutoField'
            elif field_type == 'BigIntegerField':
                return 'BigAutoField'
            elif field_type == 'SmallIntegerField':
                return 'SmallAutoField'
        if description.is_unsigned:
            if field_type == 'IntegerField':
                return 'PositiveIntegerField'
            elif field_type == 'SmallIntegerField':
                return 'PositiveSmallIntegerField'
        return field_type

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute("SHOW FULL TABLES")
        return [TableInfo(row[0], {'BASE TABLE': 't', 'VIEW': 'v'}.get(row[1]))
                for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface."
        """
        # information_schema database gives more accurate results for some figures:
        # - varchar length returned by cursor.description is an internal length,
        #   not visible length (#5725)
        # - precision and scale (for decimal fields) (#5014)
        # - auto_increment is not available in cursor.description
        cursor.execute("""
            SELECT
                column_name, data_type, character_maximum_length,
                numeric_precision, numeric_scale, extra, column_default,
                CASE
                    WHEN column_type LIKE '%% unsigned' THEN 1
                    ELSE 0
                END AS is_unsigned
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()""", [table_name])
        field_info = {line[0]: InfoLine(*line) for line in cursor.fetchall()}

        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))

        def to_int(i):
            return int(i) if i is not None else i

        fields = []
        for line in cursor.description:
            info = field_info[line[0]]
            fields.append(FieldInfo(
                *line[:3],
                to_int(info.max_len) or line[3],
                to_int(info.num_prec) or line[4],
                to_int(info.num_scale) or line[5],
                line[6],
                info.column_default,
                info.extra,
                info.is_unsigned,
            ))
        return fields

    def get_sequences(self, cursor, table_name, table_fields=()):
        for field_info in self.get_table_description(cursor, table_name):
            if 'auto_increment' in field_info.extra:
                # MySQL allows only one auto-increment column per table.
                return [{'table': table_name, 'column': field_info.name}]
        return []

    def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        constraints = self.get_key_columns(cursor, table_name)
        relations = {}
        for my_fieldname, other_table, other_field in constraints:
            relations[my_fieldname] = (other_field, other_table)
        return relations

    def get_key_columns(self, cursor, table_name):
        """
        Return a list of (column_name, referenced_table_name, referenced_column_name)
        for all key columns in the given table.
        """
        key_columns = []
        cursor.execute("""
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL""", [table_name])
        key_columns.extend(cursor.fetchall())
        return key_columns

    def get_storage_engine(self, cursor, table_name):
        """
        Retrieve the storage engine for a given table. Return the default
        storage engine if the table doesn't exist.
        """
        cursor.execute(
            "SELECT engine "
            "FROM information_schema.tables "
            "WHERE table_name = %s", [table_name])
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
                token.ttype == sqlparse.tokens.Name and
                self.connection.ops.quote_name(token.value) == token.value and
                token.value[1:-1] in columns
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
                kc.`referenced_table_name`, kc.`referenced_column_name`
            FROM information_schema.key_column_usage AS kc
            WHERE
                kc.table_schema = DATABASE() AND
                kc.table_name = %s
            ORDER BY kc.`ordinal_position`
        """
        cursor.execute(name_query, [table_name])
        for constraint, column, ref_table, ref_column in cursor.fetchall():
            if constraint not in constraints:
                constraints[constraint] = {
                    'columns': OrderedSet(),
                    'primary_key': False,
                    'unique': False,
                    'index': False,
                    'check': False,
                    'foreign_key': (ref_table, ref_column) if ref_column else None,
                }
            constraints[constraint]['columns'].add(column)
        # Now get the constraint types
        type_query = """
            SELECT c.constraint_name, c.constraint_type
            FROM information_schema.table_constraints AS c
            WHERE
                c.table_schema = DATABASE() AND
                c.table_name = %s
        """
        cursor.execute(type_query, [table_name])
        for constraint, kind in cursor.fetchall():
            if kind.lower() == "primary key":
                constraints[constraint]['primary_key'] = True
                constraints[constraint]['unique'] = True
            elif kind.lower() == "unique":
                constraints[constraint]['unique'] = True
        # Add check constraints.
        if self.connection.features.can_introspect_check_constraints:
            columns = {info.name for info in self.get_table_description(cursor, table_name)}
            type_query = """
                SELECT c.constraint_name, c.check_clause
                FROM information_schema.check_constraints AS c
                WHERE
                    c.constraint_schema = DATABASE() AND
                    c.table_name = %s
            """
            cursor.execute(type_query, [table_name])
            for constraint, check_clause in cursor.fetchall():
                constraints[constraint] = {
                    'columns': self._parse_constraint_columns(check_clause, columns),
                    'primary_key': False,
                    'unique': False,
                    'index': False,
                    'check': True,
                    'foreign_key': None,
                }
        # Now add in the indexes
        cursor.execute("SHOW INDEX FROM %s" % self.connection.ops.quote_name(table_name))
        for table, non_unique, index, colseq, column, type_ in [x[:5] + (x[10],) for x in cursor.fetchall()]:
            if index not in constraints:
                constraints[index] = {
                    'columns': OrderedSet(),
                    'primary_key': False,
                    'unique': False,
                    'check': False,
                    'foreign_key': None,
                }
            constraints[index]['index'] = True
            constraints[index]['type'] = Index.suffix if type_ == 'BTREE' else type_.lower()
            constraints[index]['columns'].add(column)
        # Convert the sorted sets to lists
        for constraint in constraints.values():
            constraint['columns'] = list(constraint['columns'])
        return constraints
