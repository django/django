import warnings

import cx_Oracle

from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo, TableInfo,
)
from django.utils.deprecation import RemovedInDjango21Warning
from django.utils.encoding import force_text


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
        # If it's a NUMBER with scale == 0, consider it an IntegerField
        if data_type == cx_Oracle.NUMBER:
            precision, scale = description[4:6]
            if scale == 0:
                if precision > 11:
                    return 'BigIntegerField'
                elif precision == 1:
                    return 'BooleanField'
                else:
                    return 'IntegerField'
            elif scale == -127:
                return 'FloatField'

        return super().get_field_type(data_type, description)

    def get_table_list(self, cursor):
        """
        Returns a list of table and view names in the current database.
        """
        cursor.execute("SELECT TABLE_NAME, 't' FROM USER_TABLES UNION ALL "
                       "SELECT VIEW_NAME, 'v' FROM USER_VIEWS")
        return [TableInfo(row[0].lower(), row[1]) for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        # user_tab_columns gives data default for columns
        cursor.execute("""
            SELECT
                column_name,
                data_default,
                CASE
                    WHEN char_used IS NULL THEN data_length
                    ELSE char_length
                END as internal_size
            FROM user_tab_cols
            WHERE table_name = UPPER(%s)""", [table_name])
        field_map = {
            column: (internal_size, default if default != 'NULL' else None)
            for column, default, internal_size in cursor.fetchall()
        }
        self.cache_bust_counter += 1
        cursor.execute("SELECT * FROM {} WHERE ROWNUM < 2 AND {} > 0".format(
            self.connection.ops.quote_name(table_name),
            self.cache_bust_counter))
        description = []
        for desc in cursor.description:
            name = force_text(desc[0])  # cx_Oracle always returns a 'str'
            internal_size, default = field_map[name]
            name = name % {}  # cx_Oracle, for some reason, doubles percent signs.
            description.append(FieldInfo(*(name.lower(),) + desc[1:3] + (internal_size,) + desc[4:] + (default,)))
        return description

    def table_name_converter(self, name):
        "Table name comparison is case insensitive under Oracle"
        return name.lower()

    def _name_to_index(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: field_index} for the given table.
        Indexes are 0-based.
        """
        return {d[0]: i for i, d in enumerate(self.get_table_description(cursor, table_name))}

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        table_name = table_name.upper()
        cursor.execute("""
    SELECT ta.column_name, tb.table_name, tb.column_name
    FROM   user_constraints, USER_CONS_COLUMNS ca, USER_CONS_COLUMNS cb,
           user_tab_cols ta, user_tab_cols tb
    WHERE  user_constraints.table_name = %s AND
           ta.table_name = user_constraints.table_name AND
           ta.column_name = ca.column_name AND
           ca.table_name = ta.table_name AND
           user_constraints.constraint_name = ca.constraint_name AND
           user_constraints.r_constraint_name = cb.constraint_name AND
           cb.table_name = tb.table_name AND
           cb.column_name = tb.column_name AND
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

    def get_indexes(self, cursor, table_name):
        warnings.warn(
            "get_indexes() is deprecated in favor of get_constraints().",
            RemovedInDjango21Warning, stacklevel=2
        )
        sql = """
    SELECT LOWER(uic1.column_name) AS column_name,
           CASE user_constraints.constraint_type
               WHEN 'P' THEN 1 ELSE 0
           END AS is_primary_key,
           CASE user_indexes.uniqueness
               WHEN 'UNIQUE' THEN 1 ELSE 0
           END AS is_unique
    FROM   user_constraints, user_indexes, user_ind_columns uic1
    WHERE  user_constraints.constraint_type (+) = 'P'
      AND  user_constraints.index_name (+) = uic1.index_name
      AND  user_indexes.uniqueness (+) = 'UNIQUE'
      AND  user_indexes.index_name (+) = uic1.index_name
      AND  uic1.table_name = UPPER(%s)
      AND  uic1.column_position = 1
      AND  NOT EXISTS (
              SELECT 1
              FROM   user_ind_columns uic2
              WHERE  uic2.index_name = uic1.index_name
                AND  uic2.column_position = 2
           )
        """
        cursor.execute(sql, [table_name])
        indexes = {}
        for row in cursor.fetchall():
            indexes[row[0]] = {'primary_key': bool(row[1]),
                               'unique': bool(row[2])}
        return indexes

    def get_constraints(self, cursor, table_name):
        """
        Retrieves any constraints or keys (unique, pk, fk, check, index) across one or more columns.
        """
        constraints = {}
        # Loop over the constraints, getting PKs, uniques, and checks
        cursor.execute("""
            SELECT
                user_constraints.constraint_name,
                LOWER(cols.column_name) AS column_name,
                CASE user_constraints.constraint_type
                    WHEN 'P' THEN 1
                    ELSE 0
                END AS is_primary_key,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM user_indexes
                        WHERE user_indexes.index_name = user_constraints.index_name
                        AND user_indexes.uniqueness = 'UNIQUE'
                    )
                    THEN 1
                    ELSE 0
                END AS is_unique,
                CASE user_constraints.constraint_type
                    WHEN 'C' THEN 1
                    ELSE 0
                END AS is_check_constraint,
                CASE
                    WHEN user_constraints.constraint_type IN ('P', 'U') THEN 1
                    ELSE 0
                END AS has_index
            FROM
                user_constraints
            LEFT OUTER JOIN
                user_cons_columns cols ON user_constraints.constraint_name = cols.constraint_name
            WHERE
                user_constraints.constraint_type = ANY('P', 'U', 'C')
                AND user_constraints.table_name = UPPER(%s)
            ORDER BY cols.position
        """, [table_name])
        for constraint, column, pk, unique, check, index in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": pk,
                    "unique": unique,
                    "foreign_key": None,
                    "check": check,
                    "index": index,  # All P and U come with index
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Foreign key constraints
        cursor.execute("""
            SELECT
                cons.constraint_name,
                LOWER(cols.column_name) AS column_name,
                LOWER(rcols.table_name),
                LOWER(rcols.column_name)
            FROM
                user_constraints cons
            INNER JOIN
                user_cons_columns rcols ON rcols.constraint_name = cons.r_constraint_name
            LEFT OUTER JOIN
                user_cons_columns cols ON cons.constraint_name = cols.constraint_name
            WHERE
                cons.constraint_type = 'R' AND
                cons.table_name = UPPER(%s)
            ORDER BY cols.position
        """, [table_name])
        for constraint, column, other_table, other_column in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": (other_table, other_column),
                    "check": False,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Now get indexes
        cursor.execute("""
            SELECT
                cols.index_name, LOWER(cols.column_name), cols.descend,
                LOWER(ind.index_type)
            FROM
                user_ind_columns cols, user_indexes ind
            WHERE
                cols.table_name = UPPER(%s) AND
                NOT EXISTS (
                    SELECT 1
                    FROM user_constraints cons
                    WHERE cols.index_name = cons.index_name
                ) AND cols.index_name = ind.index_name
            ORDER BY cols.column_position
        """, [table_name])
        for constraint, column, order, type_ in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "orders": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                    "type": 'idx' if type_ == 'normal' else type_,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
            constraints[constraint]['orders'].append(order)
        return constraints
