"""
This is the core database connection.

All Django code assumes database SELECT statements cast the resulting values as such:
    * booleans are mapped to Python booleans
    * dates are mapped to Python datetime.date objects
    * times are mapped to Python datetime.time objects
    * timestamps are mapped to Python datetime.datetime objects
"""

from django.conf.settings import DATABASE_ENGINE

try:
    dbmod = __import__('django.core.db.backends.%s' % DATABASE_ENGINE, '', '', [''])
except ImportError, exc:
    # The database backend wasn't found. Display a helpful error message
    # listing all possible database backends.
    from django.core.exceptions import ImproperlyConfigured
    import os
    backend_dir = os.path.join(__path__[0], 'backends')
    available_backends = [f[:-3] for f in os.listdir(backend_dir) if f.endswith('.py') and not f.startswith('__init__')]
    available_backends.sort()
    raise ImproperlyConfigured, "Could not load database backend: %s. Is your DATABASE_ENGINE setting (currently, %r) spelled correctly? Available options are: %s" % \
        (exc, DATABASE_ENGINE, ", ".join(map(repr, available_backends)))

DatabaseError = dbmod.DatabaseError
db = dbmod.DatabaseWrapper()
dictfetchone = dbmod.dictfetchone
dictfetchmany = dbmod.dictfetchmany
dictfetchall = dbmod.dictfetchall
dictfetchall = dbmod.dictfetchall
get_last_insert_id = dbmod.get_last_insert_id
get_date_extract_sql = dbmod.get_date_extract_sql
get_date_trunc_sql = dbmod.get_date_trunc_sql
get_limit_offset_sql = dbmod.get_limit_offset_sql
get_random_function_sql = dbmod.get_random_function_sql
get_table_list = dbmod.get_table_list
get_table_description = dbmod.get_table_description
get_relations = dbmod.get_relations
get_indexes = dbmod.get_indexes
OPERATOR_MAPPING = dbmod.OPERATOR_MAPPING
DATA_TYPES = dbmod.DATA_TYPES
DATA_TYPES_REVERSE = dbmod.DATA_TYPES_REVERSE
