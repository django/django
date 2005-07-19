"""
This is the core database connection.

All CMS code assumes database SELECT statements cast the resulting values as such:
    * booleans are mapped to Python booleans
    * dates are mapped to Python datetime.date objects
    * times are mapped to Python datetime.time objects
    * timestamps are mapped to Python datetime.datetime objects

Right now, we're handling this by using psycopg's custom typecast definitions.
If we move to a different database module, we should ensure that it either
performs the appropriate typecasting out of the box, or that it has hooks that
let us do that.
"""

from django.conf.settings import DATABASE_ENGINE

try:
    dbmod = __import__('django.core.db.backends.%s' % DATABASE_ENGINE, '', '', [''])
except ImportError:
    # The database backend wasn't found. Display a helpful error message
    # listing all possible database backends.
    from django.core.exceptions import ImproperlyConfigured
    import os
    backend_dir = os.path.join(__path__[0], 'backends')
    available_backends = [f[:-3] for f in os.listdir(backend_dir) if f.endswith('.py') and not f.startswith('__init__')]
    available_backends.sort()
    raise ImproperlyConfigured, "Your DATABASE_ENGINE setting, %r, is invalid. Is it spelled correctly? Available options are: %s" % \
        (DATABASE_ENGINE, ', '.join(map(repr, available_backends)))

DatabaseError = dbmod.DatabaseError
db = dbmod.DatabaseWrapper()
dictfetchone = dbmod.dictfetchone
dictfetchmany = dbmod.dictfetchmany
dictfetchall = dbmod.dictfetchall
dictfetchall = dbmod.dictfetchall
get_last_insert_id = dbmod.get_last_insert_id
get_date_extract_sql = dbmod.get_date_extract_sql
get_date_trunc_sql = dbmod.get_date_trunc_sql
OPERATOR_MAPPING = dbmod.OPERATOR_MAPPING
DATA_TYPES = dbmod.DATA_TYPES
