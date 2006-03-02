from django.db import transaction
from django.db.backends.sqlite3.base import quote_name

def get_table_list(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def get_table_description(cursor, table_name):
    cursor.execute("PRAGMA table_info(%s)" % quote_name(table_name))
    return [(row[1], row[2], None, None) for row in cursor.fetchall()]

def get_relations(cursor, table_name):
    raise NotImplementedError

def get_indexes(cursor, table_name):
    raise NotImplementedError

def table_exists(cursor, table_name):
    """Returns True if the given table exists."""
    try:
        cursor.execute("SELECT 1 FROM %s LIMIT 1" % quote_name(table_name))
    except:
        transaction.rollback_unless_managed()
        return False
    else:
        return True

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
                return ('CharField', {'maxlength': int(m.group(1))})
            raise KeyError

DATA_TYPES_REVERSE = FlexibleFieldLookupDict()
