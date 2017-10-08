from collections import namedtuple

import cx_Oracle

from django.db import models
from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo as BaseFieldInfo, TableInfo,
)

FieldInfo = namedtuple('FieldInfo', BaseFieldInfo._fields + ('is_autofield',))


class DatabaseIntrospection(BaseDatabaseIntrospection):
    # Maps type objects to Django Field types.
    data_types_reverse = {
        cx_Oracle.BLOB: 'BinaryField',
        cx_Oracle.CLOB: 'TextField',
        cx_Oracle.DATETIME: 'DateField',
        cx_Oracle.FIXED_CHAR: 'CharField',
        cx_Oracle.FIXED_NCHAR: 'CharField',
        cx_Oracle.NATIVE_FLOAT: 'FloatField',
        cx_Oracle.NCHAR: 'CharField',
        cx_Oracle.NCLOB: 'TextField',
        cx_Oracle.NUMBER: 'DecimalField',
        cx_Oracle.STRING: 'CharField',
        cx_Oracle.TIMESTAMP: 'DateTimeField',
    }

    cache_bust_counter = 1

    def get_field_type(self, data_type, description):
        if data_type == cx_Oracle.NUMBER:
            precision, scale = description[4:6]
            if scale == 0:
                if precision > 11:
                    return 'BigAutoField' if description.is_autofield else 'BigIntegerField'
                elif precision == 1:
                    return 'BooleanField'
                elif description.is_autofield:
                    return 'AutoField'
                else:
                    return 'IntegerField'
            elif scale == -127:
                return 'FloatField'

        return super().get_field_type(data_type, description)

    def get_table_list(self, cursor):
        """Return a list of table and view names in the current database."""
        cursor.execute("SELECT TABLE_NAME, 't' FROM USER_TABLES UNION ALL "
                       "SELECT VIEW_NAME, 'v' FROM USER_VIEWS")
        return [TableInfo(row[0].lower(), row[1]) for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        """
        Return a description of the table with the DB-API cursor.description
        interface.
        """
        # user_tab_columns gives data default for columns
        cursor.execute("""
            SELECT
                column_name,
                data_default,
                CASE
                    WHEN char_used IS NULL THEN data_length
                    ELSE char_length
                END as internal_size,
                CASE
                    WHEN identity_column = 'YES' THEN 1
                    ELSE 0
                END as is_autofield
            FROM user_tab_cols
            WHERE table_name = UPPER(%s)""", [table_name])
        field_map = {
            column: (internal_size, default if default != 'NULL' else None, is_autofield)
            for column, default, internal_size, is_autofield in cursor.fetchall()
        }
        self.cache_bust_counter += 1
        cursor.execute("SELECT * FROM {} WHERE ROWNUM < 2 AND {} > 0".format(
            self.connection.ops.quote_name(table_name),
            self.cache_bust_counter))
        description = []
        for desc in cursor.description:
            name = desc[0]
            internal_size, default, is_autofield = field_map[name]
            name = name % {}  # cx_Oracle, for some reason, doubles percent signs.
            description.append(FieldInfo(*(
                (name.lower(),) +
                desc[1:3] +
                (internal_size, desc[4] or 0, desc[5] or 0) +
                desc[6:] +
                (default, is_autofield)
            )))
        return description

    def table_name_converter(self, name):
        """Table name comparison is case insensitive under Oracle."""
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
            return [{'name': row[0].lower(), 'table': table_name, 'column': row[1].lower()}]
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

        relations = {}
        for row in cursor.fetchall():
            relations[row[0].lower()] = (row[2].lower(), row[1].lower())
        return relations

    def get_key_columns(self, cursor, table_name):
        cursor.execute("""
            SELECT ccol.column_name, rcol.table_name AS referenced_table, rcol.column_name AS referenced_column
            FROM user_constraints c
            JOIN user_cons_columns ccol
              ON ccol.constraint_name = c.constraint_name
            JOIN user_cons_columns rcol
              ON rcol.constraint_name = c.r_constraint_name
            WHERE c.table_name = %s AND c.constraint_type = 'R'""", [table_name.upper()])
        return [tuple(cell.lower() for cell in row)
                for row in cursor.fetchall()]

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
