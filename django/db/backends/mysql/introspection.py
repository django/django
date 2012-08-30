from django.db.backends import BaseDatabaseIntrospection
from django.utils import six
from MySQLdb import ProgrammingError, OperationalError
from MySQLdb.constants import FIELD_TYPE
import re

foreign_key_re = re.compile(r"\sCONSTRAINT `[^`]*` FOREIGN KEY \(`([^`]*)`\) REFERENCES `([^`]*)` \(`([^`]*)`\)")

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
        FIELD_TYPE.SHORT: 'IntegerField',
        FIELD_TYPE.STRING: 'CharField',
        FIELD_TYPE.TIMESTAMP: 'DateTimeField',
        FIELD_TYPE.TINY: 'IntegerField',
        FIELD_TYPE.TINY_BLOB: 'TextField',
        FIELD_TYPE.MEDIUM_BLOB: 'TextField',
        FIELD_TYPE.LONG_BLOB: 'TextField',
        FIELD_TYPE.VAR_STRING: 'CharField',
    }

    def get_table_list(self, cursor):
        "Returns a list of table names in the current database."
        cursor.execute("SHOW TABLES")
        return [row[0] for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        return cursor.description

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
        my_field_dict = self._name_to_index(cursor, table_name)
        constraints = self.get_key_columns(cursor, table_name)
        relations = {}
        for my_fieldname, other_table, other_field in constraints:
            other_field_index = self._name_to_index(cursor, other_table)[other_field]
            my_field_index = my_field_dict[my_fieldname]
            relations[my_field_index] = (other_field_index, other_table)
        return relations

    def get_key_columns(self, cursor, table_name):
        """
        Returns a list of (column_name, referenced_table_name, referenced_column_name) for all
        key columns in given table.
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

    def get_primary_key_column(self, cursor, table_name):
        """
        Returns the name of the primary key column for the given table
        """
        for column in six.iteritems(self.get_indexes(cursor, table_name)):
            if column[1]['primary_key']:
                return column[0]
        return None

    def get_indexes(self, cursor, table_name):
        cursor.execute("SHOW INDEX FROM %s" % self.connection.ops.quote_name(table_name))
        # Do a two-pass search for indexes: on first pass check which indexes
        # are multicolumn, on second pass check which single-column indexes
        # are present.
        rows = list(cursor.fetchall())
        multicol_indexes = set()
        for row in rows:
            if row[3] > 1:
                multicol_indexes.add(row[2])
        indexes = {}
        for row in rows:
            if row[2] in multicol_indexes:
                continue
            indexes[row[4]] = {'primary_key': (row[2] == 'PRIMARY'), 'unique': not bool(row[1])}
        return indexes

    def get_constraints(self, cursor, table_name):
        """
        Retrieves any constraints or keys (unique, pk, fk, check, index) across one or more columns.
        """
        constraints = {}
        # Get the actual constraint names and columns
        name_query = """
            SELECT kc.`constraint_name`, kc.`column_name`,
                kc.`referenced_table_name`, kc.`referenced_column_name`
            FROM information_schema.key_column_usage AS kc
            WHERE
                kc.table_schema = %s AND
                kc.table_name = %s
        """
        cursor.execute(name_query, [self.connection.settings_dict['NAME'], table_name])
        for constraint, column, ref_table, ref_column in cursor.fetchall():
            if constraint not in constraints:
                constraints[constraint] = {
                    'columns': set(),
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
                c.table_schema = %s AND
                c.table_name = %s
        """
        cursor.execute(type_query, [self.connection.settings_dict['NAME'], table_name])
        for constraint, kind in cursor.fetchall():
            if kind.lower() == "primary key":
                constraints[constraint]['primary_key'] = True
                constraints[constraint]['unique'] = True
            elif kind.lower() == "unique":
                constraints[constraint]['unique'] = True
        # Now add in the indexes
        cursor.execute("SHOW INDEX FROM %s" % self.connection.ops.quote_name(table_name))
        for table, non_unique, index, colseq, column in [x[:5] for x in cursor.fetchall()]:
            if index not in constraints:
                constraints[index] = {
                    'columns': set(),
                    'primary_key': False,
                    'unique': False,
                    'index': True,
                    'check': False,
                    'foreign_key': None,
                }
            constraints[index]['index'] = True
            constraints[index]['columns'].add(column)
        # Return
        return constraints
