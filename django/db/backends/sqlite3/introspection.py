from django.db.backends.sqlite3.base import DatabaseOperations

quote_name = DatabaseOperations().quote_name

def get_table_list(cursor):
    "Returns a list of table names in the current database."
    # Skip the sqlite_sequence system table used for autoincrement key
    # generation.
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND NOT name='sqlite_sequence'
        ORDER BY name""")
    return [row[0] for row in cursor.fetchall()]

def get_table_description(cursor, table_name):
    "Returns a description of the table, with the DB-API cursor.description interface."
    return [(info['name'], info['type'], None, None, None, None,
             info['null_ok']) for info in _table_info(cursor, table_name)]

def get_relations(cursor, table_name):
    raise NotImplementedError

def get_indexes(cursor, table_name):
    """
    Returns a dictionary of fieldname -> infodict for the given table,
    where each infodict is in the format:
        {'primary_key': boolean representing whether it's the primary key,
         'unique': boolean representing whether it's a unique index}
    """
    indexes = {}
    for info in _table_info(cursor, table_name):
        indexes[info['name']] = {'primary_key': info['pk'] != 0,
                                 'unique': False}
    cursor.execute('PRAGMA index_list(%s)' % quote_name(table_name))
    # seq, name, unique
    for index, unique in [(field[1], field[2]) for field in cursor.fetchall()]:
        if not unique:
            continue
        cursor.execute('PRAGMA index_info(%s)' % quote_name(index))
        info = cursor.fetchall()
        # Skip indexes across multiple fields
        if len(info) != 1:
            continue
        name = info[0][2] # seqno, cid, name
        indexes[name]['unique'] = True
    return indexes

def _table_info(cursor, name):
    cursor.execute('PRAGMA table_info(%s)' % quote_name(name))
    # cid, name, type, notnull, dflt_value, pk
    return [{'name': field[1],
             'type': field[2],
             'null_ok': not field[3],
             'pk': field[5]     # undocumented
             } for field in cursor.fetchall()]

# Maps SQL types to Django Field types. Some of the SQL types have multiple
# entries here because SQLite allows for anything and doesn't normalize the
# field type; it uses whatever was given.
BASE_DATA_TYPES_REVERSE = {
    'bool': 'BooleanField',
    'boolean': 'BooleanField',
    'smallint': 'SmallIntegerField',
    'smallinteger': 'SmallIntegerField',
    'int': 'IntegerField',
    'integer': 'IntegerField',
    'text': 'TextField',
    'char': 'CharField',
    'date': 'DateField',
    'datetime': 'DateTimeField',
    'time': 'TimeField',
}

# This light wrapper "fakes" a dictionary interface, because some SQLite data
# types include variables in them -- e.g. "varchar(30)" -- and can't be matched
# as a simple dictionary lookup.
class FlexibleFieldLookupDict:
    def __getitem__(self, key):
        key = key.lower()
        try:
            return BASE_DATA_TYPES_REVERSE[key]
        except KeyError:
            import re
            m = re.search(r'^\s*(?:var)?char\s*\(\s*(\d+)\s*\)\s*$', key)
            if m:
                return ('CharField', {'max_length': int(m.group(1))})
            raise KeyError

DATA_TYPES_REVERSE = FlexibleFieldLookupDict()
