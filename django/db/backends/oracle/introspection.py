from collections import namedtuple

import cx_Oracle

from django.db import models
from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo as BaseFieldInfo, TableInfo,
)
from django.utils.functional import cached_property

FieldInfo = namedtuple('FieldInfo', BaseFieldInfo._fields + ('is_autofield', 'is_json'))


class DatabaseIntrospection(BaseDatabaseIntrospection):
    cache_bust_counter = 1

    # Maps type objects to Django Field types.
    @cached_property
    def data_types_reverse(self):
        if self.connection.cx_oracle_version < (8,):
            return {
                cx_Oracle.BLOB: 'BinaryField',
                cx_Oracle.CLOB: 'TextField',
                cx_Oracle.DATETIME: 'DateField',
                cx_Oracle.FIXED_CHAR: 'CharField',
                cx_Oracle.FIXED_NCHAR: 'CharField',
                cx_Oracle.INTERVAL: 'DurationField',
                cx_Oracle.NATIVE_FLOAT: 'FloatField',
                cx_Oracle.NCHAR: 'CharField',
                cx_Oracle.NCLOB: 'TextField',
                cx_Oracle.NUMBER: 'DecimalField',
                cx_Oracle.STRING: 'CharField',
                cx_Oracle.TIMESTAMP: 'DateTimeField',
            }
        else:
            return {
                cx_Oracle.DB_TYPE_DATE: 'DateField',
                cx_Oracle.DB_TYPE_BINARY_DOUBLE: 'FloatField',
                cx_Oracle.DB_TYPE_BLOB: 'BinaryField',
                cx_Oracle.DB_TYPE_CHAR: 'CharField',
                cx_Oracle.DB_TYPE_CLOB: 'TextField',
                cx_Oracle.DB_TYPE_INTERVAL_DS: 'DurationField',
                cx_Oracle.DB_TYPE_NCHAR: 'CharField',
                cx_Oracle.DB_TYPE_NCLOB: 'TextField',
                cx_Oracle.DB_TYPE_NVARCHAR: 'CharField',
                cx_Oracle.DB_TYPE_NUMBER: 'DecimalField',
                cx_Oracle.DB_TYPE_TIMESTAMP: 'DateTimeField',
                cx_Oracle.DB_TYPE_VARCHAR: 'CharField',
            }

    def get_field_type(self, data_type, description):
        if data_type == cx_Oracle.NUMBER:
            precision, scale = description[4:6]
            if scale == 0:
                if precision > 11:
                    return 'BigAutoField' if description.is_autofield else 'BigIntegerField'
                elif 1 < precision < 6 and description.is_autofield:
                    return 'SmallAutoField'
                elif precision == 1:
                    return 'BooleanField'
                elif description.is_autofield:
                    return 'AutoField'
                else:
                    return 'IntegerField'
            elif scale == -127:
                return 'FloatField'
        elif data_type == cx_Oracle.NCLOB and description.is_json:
            return 'JSONField'

        return super().get_field_type(data_type, description)

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute("""
            SELECT table_name, 't'
            FROM user_tables
            WHERE
                NOT EXISTS (
                    SELECT 1
                    FROM user_mviews
                    WHERE user_mviews.mview_name = user_tables.table_name
                )
            UNION ALL
            SELECT view_name, 'v' FROM user_views
            UNION ALL
            SELECT mview_name, 'v' FROM user_mviews
        """)
        return [TableInfo(self.identifier_converter(row[0]), row[1]) for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        # user_tab_columns gives data default for columns
        cursor.execute("""
            SELECT
                user_tab_cols.column_name,
                user_tab_cols.data_default,
                CASE
                    WHEN user_tab_cols.collation = user_tables.default_collation
                    THEN NULL
                    ELSE user_tab_cols.collation
                END collation,
                CASE
                    WHEN user_tab_cols.char_used IS NULL
                    THEN user_tab_cols.data_length
                    ELSE user_tab_cols.char_length
                END as internal_size,
                CASE
                    WHEN user_tab_cols.identity_column = 'YES' THEN 1
                    ELSE 0
                END as is_autofield,
                CASE
                    WHEN EXISTS (
                        SELECT  1
                        FROM user_json_columns
                        WHERE
                            user_json_columns.table_name = user_tab_cols.table_name AND
                            user_json_columns.column_name = user_tab_cols.column_name
                    )
                    THEN 1
                    ELSE 0
                END as is_json
            FROM user_tab_cols
            LEFT OUTER JOIN
                user_tables ON user_tables.table_name = user_tab_cols.table_name
            WHERE user_tab_cols.table_name = UPPER(%s)
        """, [table_name])
        field_map = {
            column: (internal_size, default if default != 'NULL' else None, collation, is_autofield, is_json)
            for column, default, collation, internal_size, is_autofield, is_json in cursor.fetchall()
        }
        self.cache_bust_counter += 1
        cursor.execute("SELECT * FROM {} WHERE ROWNUM < 2 AND {} > 0".format(
            self.connection.ops.quote_name(table_name),
            self.cache_bust_counter))
        description = []
        for desc in cursor.description:
            name = desc[0]
            internal_size, default, collation, is_autofield, is_json = field_map[name]
            name = name % {}  # cx_Oracle, for some reason, doubles percent signs.
            description.append(FieldInfo(
                self.identifier_converter(name), *desc[1:3], internal_size, desc[4] or 0,
                desc[5] or 0, *desc[6:], default, collation, is_autofield, is_json,
            ))
        return description

    def identifier_converter(self, name):
        """Identifier comparison is case insensitive under Oracle."""
        return name.lower()

    def get_sequences(self, cursor, table_name, table_fields=()):
        cursor.execute("""
            SELECT
                user_tab_identity_cols.sequence_name,
                user_tab_identity_cols.column_name
            FROM
                user_tab_identity_cols,
                user_constraints,
                user_cons_columns cols
            WHERE
                user_constraints.constraint_name = cols.constraint_name
                AND user_constraints.table_name = user_tab_identity_cols.table_name
                AND cols.column_name = user_tab_identity_cols.column_name
                AND user_constraints.constraint_type = 'P'
                AND user_tab_identity_cols.table_name = UPPER(%s)
        """, [table_name])
        # Oracle allows only one identity column per table.
        row = cursor.fetchone()
        if row:
            return [{
                'name': self.identifier_converter(row[0]),
                'table': self.identifier_converter(table_name),
                'column': self.identifier_converter(row[1]),
            }]
        # To keep backward compatibility for AutoFields that aren't Oracle
        # identity columns.
        for f in table_fields:
            if isinstance(f, models.AutoField):
                return [{'table': table_name, 'column': f.column}]
        return []

    def get_relations(self, cursor, table_name):
        """
        Return a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        table_name = table_name.upper()
        cursor.execute("""
    SELECT ca.column_name, cb.table_name, cb.column_name
    FROM   user_constraints, USER_CONS_COLUMNS ca, USER_CONS_COLUMNS cb
    WHERE  user_constraints.table_name = %s AND
           user_constraints.constraint_name = ca.constraint_name AND
           user_constraints.r_constraint_name = cb.constraint_name AND
           ca.position = cb.position""", [table_name])

        return {
            self.identifier_converter(field_name): (
                self.identifier_converter(rel_field_name),
                self.identifier_converter(rel_table_name),
            ) for field_name, rel_table_name, rel_field_name in cursor.fetchall()
        }

    def get_key_columns(self, cursor, table_name):
        cursor.execute("""
            SELECT ccol.column_name, rcol.table_name AS referenced_table, rcol.column_name AS referenced_column
            FROM user_constraints c
            JOIN user_cons_columns ccol
              ON ccol.constraint_name = c.constraint_name
            JOIN user_cons_columns rcol
              ON rcol.constraint_name = c.r_constraint_name
            WHERE c.table_name = %s AND c.constraint_type = 'R'""", [table_name.upper()])
        return [
            tuple(self.identifier_converter(cell) for cell in row)
            for row in cursor.fetchall()
        ]

    def get_primary_key_column(self, cursor, table_name):
        cursor.execute("""
            SELECT
                cols.column_name
            FROM
                user_constraints,
                user_cons_columns cols
            WHERE
                user_constraints.constraint_name = cols.constraint_name AND
                user_constraints.constraint_type = 'P' AND
                user_constraints.table_name = UPPER(%s) AND
                cols.position = 1
        """, [table_name])
        row = cursor.fetchone()
        return self.identifier_converter(row[0]) if row else None

    def get_constraints(self, cursor, table_name):
        """
        Retrieve any constraints or keys (unique, pk, fk, check, index) across
        one or more columns.
        """
        constraints = {}
        # Loop over the constraints, getting PKs, uniques, and checks
        cursor.execute("""
            SELECT
                user_constraints.constraint_name,
                LISTAGG(LOWER(cols.column_name), ',') WITHIN GROUP (ORDER BY cols.position),
                CASE user_constraints.constraint_type
                    WHEN 'P' THEN 1
                    ELSE 0
                END AS is_primary_key,
                CASE
                    WHEN user_constraints.constraint_type IN ('P', 'U') THEN 1
                    ELSE 0
                END AS is_unique,
                CASE user_constraints.constraint_type
                    WHEN 'C' THEN 1
                    ELSE 0
                END AS is_check_constraint
            FROM
                user_constraints
            LEFT OUTER JOIN
                user_cons_columns cols ON user_constraints.constraint_name = cols.constraint_name
            WHERE
                user_constraints.constraint_type = ANY('P', 'U', 'C')
                AND user_constraints.table_name = UPPER(%s)
            GROUP BY user_constraints.constraint_name, user_constraints.constraint_type
        """, [table_name])
        for constraint, columns, pk, unique, check in cursor.fetchall():
            constraint = self.identifier_converter(constraint)
            constraints[constraint] = {
                'columns': columns.split(','),
                'primary_key': pk,
                'unique': unique,
                'foreign_key': None,
                'check': check,
                'index': unique,  # All uniques come with an index
            }
        # Foreign key constraints
        cursor.execute("""
            SELECT
                cons.constraint_name,
                LISTAGG(LOWER(cols.column_name), ',') WITHIN GROUP (ORDER BY cols.position),
                LOWER(rcols.table_name),
                LOWER(rcols.column_name)
            FROM
                user_constraints cons
            INNER JOIN
                user_cons_columns rcols ON rcols.constraint_name = cons.r_constraint_name AND rcols.position = 1
            LEFT OUTER JOIN
                user_cons_columns cols ON cons.constraint_name = cols.constraint_name
            WHERE
                cons.constraint_type = 'R' AND
                cons.table_name = UPPER(%s)
            GROUP BY cons.constraint_name, rcols.table_name, rcols.column_name
        """, [table_name])
        for constraint, columns, other_table, other_column in cursor.fetchall():
            constraint = self.identifier_converter(constraint)
            constraints[constraint] = {
                'primary_key': False,
                'unique': False,
                'foreign_key': (other_table, other_column),
                'check': False,
                'index': False,
                'columns': columns.split(','),
            }
        # Now get indexes
        cursor.execute("""
            SELECT
                ind.index_name,
                LOWER(ind.index_type),
                LISTAGG(LOWER(cols.column_name), ',') WITHIN GROUP (ORDER BY cols.column_position),
                LISTAGG(cols.descend, ',') WITHIN GROUP (ORDER BY cols.column_position)
            FROM
                user_ind_columns cols, user_indexes ind
            WHERE
                cols.table_name = UPPER(%s) AND
                NOT EXISTS (
                    SELECT 1
                    FROM user_constraints cons
                    WHERE ind.index_name = cons.index_name
                ) AND cols.index_name = ind.index_name
            GROUP BY ind.index_name, ind.index_type
        """, [table_name])
        for constraint, type_, columns, orders in cursor.fetchall():
            constraint = self.identifier_converter(constraint)
            constraints[constraint] = {
                'primary_key': False,
                'unique': False,
                'foreign_key': None,
                'check': False,
                'index': True,
                'type': 'idx' if type_ == 'normal' else type_,
                'columns': columns.split(','),
                'orders': orders.split(','),
            }
        return constraints
