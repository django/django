from collections import namedtuple

from MySQLdb.constants import FIELD_TYPE

from django.db.backends.base.introspection import (
    BaseDatabaseIntrospection, FieldInfo, TableInfo,
)
from django.utils.datastructures import OrderedSet
from django.utils.encoding import force_text

FieldInfo = namedtuple('FieldInfo', FieldInfo._fields + ('extra', 'default'))
InfoLine = namedtuple('InfoLine', 'col_name data_type max_len num_prec num_scale extra column_default')


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
        field_type = super(DatabaseIntrospection, self).get_field_type(data_type, description)
        if field_type == 'IntegerField' and 'auto_increment' in description.extra:
            return 'AutoField'
        return field_type

    def get_table_list(self, cursor):
        """
        Returns a list of table and view names in the current database.
        """
        cursor.execute("SHOW FULL TABLES")
        return [TableInfo(row[0], {'BASE TABLE': 't', 'VIEW': 'v'}.get(row[1]))
                for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        """
        Returns a description of the table, with the DB-API cursor.description interface."
        """
        # information_schema database gives more accurate results for some figures:
        # - varchar length returned by cursor.description is an internal length,
        #   not visible length (#5725)
        # - precision and scale (for decimal fields) (#5014)
        # - auto_increment is not available in cursor.description
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, numeric_precision,
                   numeric_scale, extra, column_default
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = DATABASE()""", [table_name])
        field_info = {line[0]: InfoLine(*line) for line in cursor.fetchall()}

        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        to_int = lambda i: int(i) if i is not None else i
        fields = []
        for line in cursor.description:
            col_name = force_text(line[0])
            fields.append(
                FieldInfo(*((col_name,)
                            + line[1:3]
                            + (to_int(field_info[col_name].max_len) or line[3],
                               to_int(field_info[col_name].num_prec) or line[4],
                               to_int(field_info[col_name].num_scale) or line[5])
                            + (line[6],)
                            + (field_info[col_name].extra,)
                            + (field_info[col_name].column_default,)))
            )
        return fields

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_name: (field_name_other_table, other_table)}
        representing all relationships to the given table.
        """
        constraints = self.get_key_columns(cursor, table_name)
        relations = {}
        for my_fieldname, other_table, other_field in constraints:
            relations[my_fieldname] = (other_field, other_table)
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
            if row[4] not in indexes:
                indexes[row[4]] = {'primary_key': False, 'unique': False}
            # It's possible to have the unique and PK constraints in separate indexes.
            if row[2] == 'PRIMARY':
                indexes[row[4]]['primary_key'] = True
            if not row[1]:
                indexes[row[4]]['unique'] = True
        return indexes

    def get_storage_engine(self, cursor, table_name):
        """
        Retrieves the storage engine for a given table. Returns the default
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
                    'columns': OrderedSet(),
                    'primary_key': False,
                    'unique': False,
                    'index': True,
                    'check': False,
                    'foreign_key': None,
                }
            constraints[index]['index'] = True
            constraints[index]['columns'].add(column)
        # Convert the sorted sets to lists
        for constraint in constraints.values():
            constraint['columns'] = list(constraint['columns'])
        return constraints
