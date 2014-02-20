import re

import cx_Oracle

from django.db.backends import BaseDatabaseIntrospection, FieldInfo
from django.utils.encoding import force_text

foreign_key_re = re.compile(r"\sCONSTRAINT `[^`]*` FOREIGN KEY \(`([^`]*)`\) REFERENCES `([^`]*)` \(`([^`]*)`\)")


class DatabaseIntrospection(BaseDatabaseIntrospection):
    # Maps type objects to Django Field types.
    data_types_reverse = {
        cx_Oracle.BLOB: 'BinaryField',
        cx_Oracle.CLOB: 'TextField',
        cx_Oracle.DATETIME: 'DateField',
        cx_Oracle.FIXED_CHAR: 'CharField',
        cx_Oracle.NCLOB: 'TextField',
        cx_Oracle.NUMBER: 'DecimalField',
        cx_Oracle.STRING: 'CharField',
        cx_Oracle.TIMESTAMP: 'DateTimeField',
    }

    try:
        data_types_reverse[cx_Oracle.NATIVE_FLOAT] = 'FloatField'
    except AttributeError:
        pass

    try:
        data_types_reverse[cx_Oracle.UNICODE] = 'CharField'
    except AttributeError:
        pass

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

        return super(DatabaseIntrospection, self).get_field_type(data_type, description)

    def get_table_list(self, cursor):
        "Returns a list of table names in the current database."
        cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
        return [row[0].lower() for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        cursor.execute("SELECT * FROM %s WHERE ROWNUM < 2" % self.connection.ops.quote_name(table_name))
        description = []
        for desc in cursor.description:
            name = force_text(desc[0])  # cx_Oracle always returns a 'str' on both Python 2 and 3
            name = name % {}  # cx_Oracle, for some reason, doubles percent signs.
            description.append(FieldInfo(*(name.lower(),) + desc[1:]))
        return description

    def table_name_converter(self, name):
        "Table name comparison is case insensitive under Oracle"
        return name.lower()

    def _name_to_index(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: field_index} for the given table.
        Indexes are 0-based.
        """
        return dict((d[0], i) for i, d in enumerate(self.get_table_description(cursor, table_name)))

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
        representing all relationships to the given table. Indexes are 0-based.
        """
        table_name = table_name.upper()
        cursor.execute("""
    SELECT ta.column_id - 1, tb.table_name, tb.column_id - 1
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
            relations[row[0]] = (row[2], row[1].lower())
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
        # Loop over the constraints, getting PKs and uniques
        cursor.execute("""
            SELECT
                user_constraints.constraint_name,
                LOWER(cols.column_name) AS column_name,
                CASE user_constraints.constraint_type
                    WHEN 'P' THEN 1
                    ELSE 0
                END AS is_primary_key,
                CASE user_indexes.uniqueness
                    WHEN 'UNIQUE' THEN 1
                    ELSE 0
                END AS is_unique,
                CASE user_constraints.constraint_type
                    WHEN 'C' THEN 1
                    ELSE 0
                END AS is_check_constraint
            FROM
                user_constraints
            INNER JOIN
                user_indexes ON user_indexes.index_name = user_constraints.index_name
            LEFT OUTER JOIN
                user_cons_columns cols ON user_constraints.constraint_name = cols.constraint_name
            WHERE
                (
                    user_constraints.constraint_type = 'P' OR
                    user_constraints.constraint_type = 'U'
                )
                AND user_constraints.table_name = UPPER(%s)
            ORDER BY cols.position
        """, [table_name])
        for constraint, column, pk, unique, check in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": pk,
                    "unique": unique,
                    "foreign_key": None,
                    "check": check,
                    "index": True,  # All P and U come with index, see inner join above
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Check constraints
        cursor.execute("""
            SELECT
                cons.constraint_name,
                LOWER(cols.column_name) AS column_name
            FROM
                user_constraints cons
            LEFT OUTER JOIN
                user_cons_columns cols ON cons.constraint_name = cols.constraint_name
            WHERE
                cons.constraint_type = 'C' AND
                cons.table_name = UPPER(%s)
            ORDER BY cols.position
        """, [table_name])
        for constraint, column in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": True,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Foreign key constraints
        cursor.execute("""
            SELECT
                cons.constraint_name,
                LOWER(cols.column_name) AS column_name,
                LOWER(rcons.table_name),
                LOWER(rcols.column_name)
            FROM
                user_constraints cons
            INNER JOIN
                user_constraints rcons ON cons.r_constraint_name = rcons.constraint_name
            INNER JOIN
                user_cons_columns rcols ON rcols.constraint_name = rcons.constraint_name
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
                index_name,
                LOWER(column_name)
            FROM
                user_ind_columns cols
            WHERE
                table_name = UPPER(%s) AND
                NOT EXISTS (
                    SELECT 1
                    FROM user_constraints cons
                    WHERE cols.index_name = cons.index_name
                )
            ORDER BY cols.column_position
        """, [table_name])
        for constraint, column in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        return constraints
