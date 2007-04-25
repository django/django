"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

from django.db.backends import util
try:
    import psycopg2 as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading psycopg2 module: %s" % e

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

postgres_version = None

class DatabaseWrapper(local):
    def __init__(self, **kwargs):
        self.connection = None
        self.queries = []
        self.options = kwargs

    def cursor(self):
        from django.conf import settings
        set_tz = False
        if self.connection is None:
            set_tz = True
            if settings.DATABASE_NAME == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "You need to specify DATABASE_NAME in your Django settings file."
            conn_string = "dbname=%s" % settings.DATABASE_NAME
            if settings.DATABASE_USER:
                conn_string = "user=%s %s" % (settings.DATABASE_USER, conn_string)
            if settings.DATABASE_PASSWORD:
                conn_string += " password='%s'" % settings.DATABASE_PASSWORD
            if settings.DATABASE_HOST:
                conn_string += " host=%s" % settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                conn_string += " port=%s" % settings.DATABASE_PORT
            self.connection = Database.connect(conn_string, **self.options)
            self.connection.set_isolation_level(1) # make transactions transparent to all cursors
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = None
        if set_tz:
            cursor.execute("SET TIME ZONE %s", [settings.TIME_ZONE])
        global postgres_version
        if not postgres_version:
            cursor.execute("SELECT version()")
            postgres_version = [int(val) for val in cursor.fetchone()[0].split()[1].split('.')]
        if settings.DEBUG:
            return util.CursorDebugWrapper(cursor, self)
        return cursor

    def _commit(self):
        if self.connection is not None:
            return self.connection.commit()

    def _rollback(self):
        if self.connection is not None:
            return self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

allows_group_by_ordinal = True
allows_unique_and_pk = True
autoindexes_primary_keys = True
needs_datetime_string_cast = False
needs_upper_for_iops = False
supports_constraints = True
supports_tablespaces = False
uses_case_insensitive_names = True

def quote_name(name):
    if name.startswith('"') and name.endswith('"'):
        return name # Quoting once is enough.
    return '"%s"' % name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute("SELECT CURRVAL('\"%s_%s_seq\"')" % (table_name, pk_name))
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
    return "EXTRACT('%s' FROM %s)" % (lookup_type, table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
    return "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)

def get_datetime_cast_sql():
    return None

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT %s" % limit
    if offset and offset != 0:
        sql += " OFFSET %s" % offset
    return sql

def get_random_function_sql():
    return "RANDOM()"

def get_deferrable_sql():
    return " DEFERRABLE INITIALLY DEFERRED"

def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return "DROP CONSTRAINT"

def get_pk_default_value():
    return "DEFAULT"

def get_max_name_length():
    return None

def get_start_transaction_sql():
    return "BEGIN;"

def get_autoinc_sql(table):
    return None

def get_sql_flush(style, tables, sequences):
    """Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state
    """
    if tables:
        if postgres_version[0] >= 8 and postgres_version[1] >= 1:
            # Postgres 8.1+ can do 'TRUNCATE x, y, z...;'. In fact, it *has to* in order to be able to
            # truncate tables referenced by a foreign key in any other table. The result is a
            # single SQL TRUNCATE statement
            sql = ['%s %s;' % \
                    (style.SQL_KEYWORD('TRUNCATE'),
                     style.SQL_FIELD(', '.join([quote_name(table) for table in tables]))
                    )]
        else:
            sql = ['%s %s %s;' % \
                    (style.SQL_KEYWORD('DELETE'),
                     style.SQL_KEYWORD('FROM'),
                     style.SQL_FIELD(quote_name(table))
                     ) for table in tables]

        # 'ALTER SEQUENCE sequence_name RESTART WITH 1;'... style SQL statements
        # to reset sequence indices
        for sequence in sequences:
            table_name = sequence['table']
            column_name = sequence['column']
            if column_name and len(column_name) > 0:
                # sequence name in this case will be <table>_<column>_seq
                sql.append("%s %s %s %s %s %s;" % \
                    (style.SQL_KEYWORD('ALTER'),
                     style.SQL_KEYWORD('SEQUENCE'),
                     style.SQL_FIELD(quote_name('%s_%s_seq' % (table_name, column_name))),
                     style.SQL_KEYWORD('RESTART'),
                     style.SQL_KEYWORD('WITH'),
                     style.SQL_FIELD('1')
                     )
                )
            else:
                # sequence name in this case will be <table>_id_seq
                sql.append("%s %s %s %s %s %s;" % \
                    (style.SQL_KEYWORD('ALTER'),
                     style.SQL_KEYWORD('SEQUENCE'),
                     style.SQL_FIELD(quote_name('%s_id_seq' % table_name)),
                     style.SQL_KEYWORD('RESTART'),
                     style.SQL_KEYWORD('WITH'),
                     style.SQL_FIELD('1')
                     )
                )
        return sql
    else:
        return []

def get_sql_sequence_reset(style, model_list):
    "Returns a list of the SQL statements to reset sequences for the given models."
    from django.db import models
    output = []
    for model in model_list:
        for f in model._meta.fields:
            if isinstance(f, models.AutoField):
                output.append("%s setval('%s', (%s max(%s) %s %s));" % \
                    (style.SQL_KEYWORD('SELECT'),
                    style.SQL_FIELD('%s_%s_seq' % (model._meta.db_table, f.column)),
                    style.SQL_KEYWORD('SELECT'),
                    style.SQL_FIELD(quote_name(f.column)),
                    style.SQL_KEYWORD('FROM'),
                    style.SQL_TABLE(quote_name(model._meta.db_table))))
                break # Only one AutoField is allowed per model, so don't bother continuing.
        for f in model._meta.many_to_many:
            output.append("%s setval('%s', (%s max(%s) %s %s));" % \
                (style.SQL_KEYWORD('SELECT'),
                style.SQL_FIELD('%s_id_seq' % f.m2m_db_table()),
                style.SQL_KEYWORD('SELECT'),
                style.SQL_FIELD(quote_name('id')),
                style.SQL_KEYWORD('FROM'),
                style.SQL_TABLE(f.m2m_db_table())))
    return output

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'ILIKE %s',
    'contains': 'LIKE %s',
    'icontains': 'ILIKE %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE %s',
    'endswith': 'LIKE %s',
    'istartswith': 'ILIKE %s',
    'iendswith': 'ILIKE %s',
}
