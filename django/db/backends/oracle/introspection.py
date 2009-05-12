from django.db.backends import BaseDatabaseIntrospection
import cx_Oracle
import re

foreign_key_re = re.compile(r"\sCONSTRAINT `[^`]*` FOREIGN KEY \(`([^`]*)`\) REFERENCES `([^`]*)` \(`([^`]*)`\)")

class DatabaseIntrospection(BaseDatabaseIntrospection):
    # Maps type objects to Django Field types.
    data_types_reverse = {
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

    def get_table_list(self, cursor):
        "Returns a list of table names in the current database."
        cursor.execute("SELECT TABLE_NAME FROM USER_TABLES")
        return [row[0].lower() for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        cursor.execute("SELECT * FROM %s WHERE ROWNUM < 2" % self.connection.ops.quote_name(table_name))
        description = []
        for desc in cursor.description:
            description.append((desc[0].lower(),) + desc[1:])
        return description

    def table_name_converter(self, name):
        "Table name comparison is case insensitive under Oracle"
        return name.lower()

    def _name_to_index(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: field_index} for the given table.
        Indexes are 0-based.
        """
        return dict([(d[0], i) for i, d in enumerate(self.get_table_description(cursor, table_name))])

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
        representing all relationships to the given table. Indexes are 0-based.
        """
        cursor.execute("""
    SELECT ta.column_id - 1, tb.table_name, tb.column_id - 1
    FROM   user_constraints, USER_CONS_COLUMNS ca, USER_CONS_COLUMNS cb,
           user_tab_cols ta, user_tab_cols tb
    WHERE  user_constraints.table_name = %s AND
           ta.table_name = %s AND
           ta.column_name = ca.column_name AND
           ca.table_name = %s AND
           user_constraints.constraint_name = ca.constraint_name AND
           user_constraints.r_constraint_name = cb.constraint_name AND
           cb.table_name = tb.table_name AND
           cb.column_name = tb.column_name AND
           ca.position = cb.position""", [table_name, table_name, table_name])

        relations = {}
        for row in cursor.fetchall():
            relations[row[0]] = (row[2], row[1])
        return relations

    def get_indexes(self, cursor, table_name):
        """
        Returns a dictionary of fieldname -> infodict for the given table,
        where each infodict is in the format:
            {'primary_key': boolean representing whether it's the primary key,
             'unique': boolean representing whether it's a unique index}
        """
        # This query retrieves each index on the given table, including the
        # first associated field name
        # "We were in the nick of time; you were in great peril!"
        sql = """\
SELECT LOWER(all_tab_cols.column_name) AS column_name,
       CASE user_constraints.constraint_type
           WHEN 'P' THEN 1 ELSE 0
       END AS is_primary_key,
       CASE user_indexes.uniqueness
           WHEN 'UNIQUE' THEN 1 ELSE 0
       END AS is_unique
FROM   all_tab_cols, user_cons_columns, user_constraints, user_ind_columns, user_indexes
WHERE  all_tab_cols.column_name = user_cons_columns.column_name (+)
  AND  all_tab_cols.table_name = user_cons_columns.table_name (+)
  AND  user_cons_columns.constraint_name = user_constraints.constraint_name (+)
  AND  user_constraints.constraint_type (+) = 'P'
  AND  user_ind_columns.column_name (+) = all_tab_cols.column_name
  AND  user_ind_columns.table_name (+) = all_tab_cols.table_name
  AND  user_indexes.uniqueness (+) = 'UNIQUE'
  AND  user_indexes.index_name (+) = user_ind_columns.index_name
  AND  all_tab_cols.table_name = UPPER(%s)
"""
        cursor.execute(sql, [table_name])
        indexes = {}
        for row in cursor.fetchall():
            indexes[row[0]] = {'primary_key': row[1], 'unique': row[2]}
        return indexes
