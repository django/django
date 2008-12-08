"""
Oracle database backend for Django.

Requires cx_Oracle: http://www.python.net/crew/atuining/cx_Oracle/
"""

import os
import datetime
import time

# Oracle takes client-side character set encoding from the environment.
os.environ['NLS_LANG'] = '.UTF8'
try:
    import cx_Oracle as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading cx_Oracle module: %s" % e)

from django.db.backends import *
from django.db.backends.oracle import query
from django.db.backends.oracle.client import DatabaseClient
from django.db.backends.oracle.creation import DatabaseCreation
from django.db.backends.oracle.introspection import DatabaseIntrospection
from django.utils.encoding import smart_str, force_unicode

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    needs_datetime_string_cast = False
    uses_custom_query_class = True
    interprets_empty_strings_as_nulls = True


class DatabaseOperations(BaseDatabaseOperations):
    def autoinc_sql(self, table, column):
        # To simulate auto-incrementing primary keys in Oracle, we have to
        # create a sequence and a trigger.
        sq_name = get_sequence_name(table)
        tr_name = get_trigger_name(table)
        tbl_name = self.quote_name(table)
        col_name = self.quote_name(column)
        sequence_sql = """
            DECLARE
                i INTEGER;
            BEGIN
                SELECT COUNT(*) INTO i FROM USER_CATALOG
                    WHERE TABLE_NAME = '%(sq_name)s' AND TABLE_TYPE = 'SEQUENCE';
                IF i = 0 THEN
                    EXECUTE IMMEDIATE 'CREATE SEQUENCE "%(sq_name)s"';
                END IF;
            END;
            /""" % locals()
        trigger_sql = """
            CREATE OR REPLACE TRIGGER "%(tr_name)s"
            BEFORE INSERT ON %(tbl_name)s
            FOR EACH ROW
            WHEN (new.%(col_name)s IS NULL)
                BEGIN
                    SELECT "%(sq_name)s".nextval
                    INTO :new.%(col_name)s FROM dual;
                END;
                /""" % locals()
        return sequence_sql, trigger_sql

    def date_extract_sql(self, lookup_type, field_name):
        # http://download-east.oracle.com/docs/cd/B10501_01/server.920/a96540/functions42a.htm#1017163
        return "EXTRACT(%s FROM %s)" % (lookup_type, field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # Oracle uses TRUNC() for both dates and numbers.
        # http://download-east.oracle.com/docs/cd/B10501_01/server.920/a96540/functions155a.htm#SQLRF06151
        if lookup_type == 'day':
            sql = 'TRUNC(%s)' % field_name
        else:
            sql = "TRUNC(%s, '%s')" % (field_name, lookup_type)
        return sql

    def datetime_cast_sql(self):
        return "TO_TIMESTAMP(%s, 'YYYY-MM-DD HH24:MI:SS.FF')"

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def drop_sequence_sql(self, table):
        return "DROP SEQUENCE %s;" % self.quote_name(get_sequence_name(table))

    def field_cast_sql(self, db_type):
        if db_type and db_type.endswith('LOB'):
            return "DBMS_LOB.SUBSTR(%s)"
        else:
            return "%s"

    def last_insert_id(self, cursor, table_name, pk_name):
        sq_name = get_sequence_name(table_name)
        cursor.execute('SELECT "%s".currval FROM dual' % sq_name)
        return cursor.fetchone()[0]

    def lookup_cast(self, lookup_type):
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            return "UPPER(%s)"
        return "%s"

    def max_name_length(self):
        return 30

    def prep_for_iexact_query(self, x):
        return x

    def query_class(self, DefaultQueryClass):
        return query.query_class(DefaultQueryClass, Database)

    def quote_name(self, name):
        # SQL92 requires delimited (quoted) names to be case-sensitive.  When
        # not quoted, Oracle has case-insensitive behavior for identifiers, but
        # always defaults to uppercase.
        # We simplify things by making Oracle identifiers always uppercase.
        if not name.startswith('"') and not name.endswith('"'):
            name = '"%s"' % util.truncate_name(name.upper(), self.max_name_length())
        return name.upper()

    def random_function_sql(self):
        return "DBMS_RANDOM.RANDOM"

    def regex_lookup_9(self, lookup_type):
        raise NotImplementedError("Regexes are not supported in Oracle before version 10g.")

    def regex_lookup_10(self, lookup_type):
        if lookup_type == 'regex':
            match_option = "'c'"
        else:
            match_option = "'i'"
        return 'REGEXP_LIKE(%%s, %%s, %s)' % match_option

    def regex_lookup(self, lookup_type):
        # If regex_lookup is called before it's been initialized, then create
        # a cursor to initialize it and recur.
        from django.db import connection
        connection.cursor()
        return connection.ops.regex_lookup(lookup_type)

    def sql_flush(self, style, tables, sequences):
        # Return a list of 'TRUNCATE x;', 'TRUNCATE y;',
        # 'TRUNCATE z;'... style SQL statements
        if tables:
            # Oracle does support TRUNCATE, but it seems to get us into
            # FK referential trouble, whereas DELETE FROM table works.
            sql = ['%s %s %s;' % \
                    (style.SQL_KEYWORD('DELETE'),
                     style.SQL_KEYWORD('FROM'),
                     style.SQL_FIELD(self.quote_name(table))
                     ) for table in tables]
            # Since we've just deleted all the rows, running our sequence
            # ALTER code will reset the sequence to 0.
            for sequence_info in sequences:
                sequence_name = get_sequence_name(sequence_info['table'])
                table_name = self.quote_name(sequence_info['table'])
                column_name = self.quote_name(sequence_info['column'] or 'id')
                query = _get_sequence_reset_sql() % {'sequence': sequence_name,
                                                     'table': table_name,
                                                     'column': column_name}
                sql.append(query)
            return sql
        else:
            return []

    def sequence_reset_sql(self, style, model_list):
        from django.db import models
        output = []
        query = _get_sequence_reset_sql()
        for model in model_list:
            for f in model._meta.local_fields:
                if isinstance(f, models.AutoField):
                    table_name = self.quote_name(model._meta.db_table)
                    sequence_name = get_sequence_name(model._meta.db_table)
                    column_name = self.quote_name(f.column)
                    output.append(query % {'sequence': sequence_name,
                                           'table': table_name,
                                           'column': column_name})
                    break # Only one AutoField is allowed per model, so don't bother continuing.
            for f in model._meta.many_to_many:
                table_name = self.quote_name(f.m2m_db_table())
                sequence_name = get_sequence_name(f.m2m_db_table())
                column_name = self.quote_name('id')
                output.append(query % {'sequence': sequence_name,
                                       'table': table_name,
                                       'column': column_name})
        return output

    def start_transaction_sql(self):
        return ''

    def tablespace_sql(self, tablespace, inline=False):
        return "%sTABLESPACE %s" % ((inline and "USING INDEX " or ""), self.quote_name(tablespace))

    def value_to_db_time(self, value):
        if value is None:
            return None
        if isinstance(value, basestring):
            return datetime.datetime(*(time.strptime(value, '%H:%M:%S')[:6]))
        return datetime.datetime(1900, 1, 1, value.hour, value.minute,
                                 value.second, value.microsecond)

    def year_lookup_bounds_for_date_field(self, value):
        first = '%s-01-01'
        second = '%s-12-31'
        return [first % value, second % value]


class DatabaseWrapper(BaseDatabaseWrapper):

    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': "LIKEC %s ESCAPE '\\'",
        'icontains': "LIKEC UPPER(%s) ESCAPE '\\'",
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKEC %s ESCAPE '\\'",
        'endswith': "LIKEC %s ESCAPE '\\'",
        'istartswith': "LIKEC UPPER(%s) ESCAPE '\\'",
        'iendswith': "LIKEC UPPER(%s) ESCAPE '\\'",
    }
    oracle_version = None

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.client = DatabaseClient()
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation()

    def _valid_connection(self):
        return self.connection is not None

    def _cursor(self, settings):
        cursor = None
        if not self._valid_connection():
            if len(settings.DATABASE_HOST.strip()) == 0:
                settings.DATABASE_HOST = 'localhost'
            if len(settings.DATABASE_PORT.strip()) != 0:
                dsn = Database.makedsn(settings.DATABASE_HOST, int(settings.DATABASE_PORT), settings.DATABASE_NAME)
                self.connection = Database.connect(settings.DATABASE_USER, settings.DATABASE_PASSWORD, dsn, **self.options)
            else:
                conn_string = "%s/%s@%s" % (settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME)
                self.connection = Database.connect(conn_string, **self.options)
            cursor = FormatStylePlaceholderCursor(self.connection)
            # Set oracle date to ansi date format.  This only needs to execute
            # once when we create a new connection.
            cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD' "
                           "NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")
            try:
                self.oracle_version = int(self.connection.version.split('.')[0])
                # There's no way for the DatabaseOperations class to know the
                # currently active Oracle version, so we do some setups here.
                # TODO: Multi-db support will need a better solution (a way to
                # communicate the current version).
                if self.oracle_version <= 9:
                    self.ops.regex_lookup = self.ops.regex_lookup_9
                else:
                    self.ops.regex_lookup = self.ops.regex_lookup_10
            except ValueError:
                pass
            try:
                self.connection.stmtcachesize = 20
            except:
                # Django docs specify cx_Oracle version 4.3.1 or higher, but
                # stmtcachesize is available only in 4.3.2 and up.
                pass
        if not cursor:
            cursor = FormatStylePlaceholderCursor(self.connection)
        # Default arraysize of 1 is highly sub-optimal.
        cursor.arraysize = 100
        return cursor


class OracleParam(object):
    """
    Wrapper object for formatting parameters for Oracle. If the string
    representation of the value is large enough (greater than 4000 characters)
    the input size needs to be set as NCLOB. Alternatively, if the parameter has
    an `input_size` attribute, then the value of the `input_size` attribute will
    be used instead. Otherwise, no input size will be set for the parameter when
    executing the query.
    """
    def __init__(self, param, charset, strings_only=False):
        self.smart_str = smart_str(param, charset, strings_only)
        if hasattr(param, 'input_size'):
            # If parameter has `input_size` attribute, use that.
            self.input_size = param.input_size
        elif isinstance(param, basestring) and len(param) > 4000:
            # Mark any string parameter greater than 4000 characters as an NCLOB.
            self.input_size = Database.NCLOB
        else:
            self.input_size = None


class FormatStylePlaceholderCursor(Database.Cursor):
    """
    Django uses "format" (e.g. '%s') style placeholders, but Oracle uses ":var"
    style. This fixes it -- but note that if you want to use a literal "%s" in
    a query, you'll need to use "%%s".

    We also do automatic conversion between Unicode on the Python side and
    UTF-8 -- for talking to Oracle -- in here.
    """
    charset = 'utf-8'

    def _format_params(self, params):
        return tuple([OracleParam(p, self.charset, True) for p in params])

    def _guess_input_sizes(self, params_list):
        sizes = [None] * len(params_list[0])
        for params in params_list:
            for i, value in enumerate(params):
                if value.input_size: sizes[i] = value.input_size
        self.setinputsizes(*sizes)

    def _param_generator(self, params):
        return [p.smart_str for p in params]

    def execute(self, query, params=None):
        if params is None:
            params = []
        else:
            params = self._format_params(params)
        args = [(':arg%d' % i) for i in range(len(params))]
        # cx_Oracle wants no trailing ';' for SQL statements.  For PL/SQL, it
        # it does want a trailing ';' but not a trailing '/'.  However, these
        # characters must be included in the original query in case the query
        # is being passed to SQL*Plus.
        if query.endswith(';') or query.endswith('/'):
            query = query[:-1]
        query = smart_str(query, self.charset) % tuple(args)
        self._guess_input_sizes([params])
        try:
            return Database.Cursor.execute(self, query, self._param_generator(params))
        except DatabaseError, e:
            # cx_Oracle <= 4.4.0 wrongly raises a DatabaseError for ORA-01400.
            if e.args[0].code == 1400 and not isinstance(e, IntegrityError):
                e = IntegrityError(e.args[0])
            raise e

    def executemany(self, query, params=None):
        try:
          args = [(':arg%d' % i) for i in range(len(params[0]))]
        except (IndexError, TypeError):
          # No params given, nothing to do
          return None
        # cx_Oracle wants no trailing ';' for SQL statements.  For PL/SQL, it
        # it does want a trailing ';' but not a trailing '/'.  However, these
        # characters must be included in the original query in case the query
        # is being passed to SQL*Plus.
        if query.endswith(';') or query.endswith('/'):
            query = query[:-1]
        query = smart_str(query, self.charset) % tuple(args)
        formatted = [self._format_params(i) for i in params]
        self._guess_input_sizes(formatted)
        try:
            return Database.Cursor.executemany(self, query, [self._param_generator(p) for p in formatted])
        except DatabaseError, e:
            # cx_Oracle <= 4.4.0 wrongly raises a DatabaseError for ORA-01400.
            if e.args[0].code == 1400 and not isinstance(e, IntegrityError):
                e = IntegrityError(e.args[0])
            raise e

    def fetchone(self):
        row = Database.Cursor.fetchone(self)
        if row is None:
            return row
        return tuple([to_unicode(e) for e in row])

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize
        return tuple([tuple([to_unicode(e) for e in r]) for r in Database.Cursor.fetchmany(self, size)])

    def fetchall(self):
        return tuple([tuple([to_unicode(e) for e in r]) for r in Database.Cursor.fetchall(self)])

def to_unicode(s):
    """
    Convert strings to Unicode objects (and return all other data types
    unchanged).
    """
    if isinstance(s, basestring):
        return force_unicode(s)
    return s

def _get_sequence_reset_sql():
    # TODO: colorize this SQL code with style.SQL_KEYWORD(), etc.
    return """
        DECLARE
            startvalue integer;
            cval integer;
        BEGIN
            LOCK TABLE %(table)s IN SHARE MODE;
            SELECT NVL(MAX(%(column)s), 0) INTO startvalue FROM %(table)s;
            SELECT "%(sequence)s".nextval INTO cval FROM dual;
            cval := startvalue - cval;
            IF cval != 0 THEN
                EXECUTE IMMEDIATE 'ALTER SEQUENCE "%(sequence)s" MINVALUE 0 INCREMENT BY '||cval;
                SELECT "%(sequence)s".nextval INTO cval FROM dual;
                EXECUTE IMMEDIATE 'ALTER SEQUENCE "%(sequence)s" INCREMENT BY 1';
            END IF;
            COMMIT;
        END;
        /"""

def get_sequence_name(table):
    name_length = DatabaseOperations().max_name_length() - 3
    return '%s_SQ' % util.truncate_name(table, name_length).upper()

def get_trigger_name(table):
    name_length = DatabaseOperations().max_name_length() - 3
    return '%s_TR' % util.truncate_name(table, name_length).upper()
