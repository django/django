import re
from .base import FIELD_TYPE

from django.db.backends import BaseDatabaseIntrospection, FieldInfo
from django.utils.encoding import force_text


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
        FIELD_TYPE.TIME: 'TimeField',
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
        """
        Returns a description of the table, with the DB-API cursor.description interface."
        """
        # varchar length returned by cursor.description is an internal length,
        # not visible length (#5725), use information_schema database to fix this
        cursor.execute("""
            SELECT column_name, character_maximum_length FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()
                AND character_maximum_length IS NOT NULL""", [table_name])
        length_map = dict(cursor.fetchall())

        # Also getting precision and scale from information_schema (see #5014)
        cursor.execute("""
            SELECT column_name, numeric_precision, numeric_scale FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()
                AND data_type='decimal'""", [table_name])
        numeric_map = dict([(line[0], tuple([int(n) for n in line[1:]])) for line in cursor.fetchall()])

        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        return [FieldInfo(*((force_text(line[0]),)
                            + line[1:3]
                            + (length_map.get(line[0], line[3]),)
                            + numeric_map.get(line[0], line[4:6])
                            + (line[6],)))
            for line in cursor.description]

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
