"""
Oracle database backend for Django.

Requires cx_Oracle: http://www.python.net/crew/atuining/cx_Oracle/
"""

import datetime
import os

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseOperations, util
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_str, force_unicode

# Oracle takes client-side character set encoding from the environment.
os.environ['NLS_LANG'] = '.UTF8'
try:
    import cx_Oracle as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading cx_Oracle module: %s" % e)

DatabaseError = Database.Error
IntegrityError = Database.IntegrityError

class DatabaseFeatures(BaseDatabaseFeatures):
    allows_group_by_ordinal = False
    allows_unique_and_pk = False        # Suppress UNIQUE/PK for Oracle (ORA-02259)
    empty_fetchmany_value = ()
    needs_datetime_string_cast = False
    needs_upper_for_iops = True
    supports_tablespaces = True
    uses_case_insensitive_names = True
    uses_custom_queryset = True

class DatabaseOperations(BaseDatabaseOperations):
    def autoinc_sql(self, table, column):
        # To simulate auto-incrementing primary keys in Oracle, we have to
        # create a sequence and a trigger.
        sq_name = get_sequence_name(table)
        tr_name = get_trigger_name(table)
        tbl_name = self.quote_name(table)
        col_name = self.quote_name(column)
        sequence_sql = 'CREATE SEQUENCE %s;' % sq_name
        trigger_sql = """
            CREATE OR REPLACE TRIGGER %(tr_name)s
            BEFORE INSERT ON %(tbl_name)s
            FOR EACH ROW
            WHEN (new.%(col_name)s IS NULL)
                BEGIN
                    SELECT %(sq_name)s.nextval
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
        sq_name = util.truncate_name(table_name, self.max_name_length() - 3)
        cursor.execute('SELECT %s_sq.currval FROM dual' % sq_name)
        return cursor.fetchone()[0]

    def limit_offset_sql(self, limit, offset=None):
        # Limits and offset are too complicated to be handled here.
        # Instead, they are handled in django/db/backends/oracle/query.py.
        return ""

    def lookup_cast(self, lookup_type):
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            return "UPPER(%s)"
        return "%s"

    def max_name_length(self):
        return 30

    def query_set_class(self, DefaultQuerySet):
        # Getting the base default `Query` object.
        DefaultQuery = DefaultQuerySet().query.__class__

        class OracleQuery(DefaultQuery):
            def resolve_columns(self, row, fields=()):
                from django.db.models.fields import DateField, DateTimeField, \
                     TimeField, BooleanField, NullBooleanField, DecimalField, Field
                values = []
                for value, field in map(None, row, fields):
                    if isinstance(value, Database.LOB):
                        value = value.read()
                    # Oracle stores empty strings as null. We need to undo this in
                    # order to adhere to the Django convention of using the empty
                    # string instead of null, but only if the field accepts the
                    # empty string.
                    if value is None and isinstance(field, Field) and field.empty_strings_allowed:
                        value = u''
                    # Convert 1 or 0 to True or False
                    elif value in (1, 0) and isinstance(field, (BooleanField, NullBooleanField)):
                        value = bool(value)
                    # Convert floats to decimals
                    elif value is not None and isinstance(field, DecimalField):
                        value = util.typecast_decimal(field.format_number(value))
                    # cx_Oracle always returns datetime.datetime objects for
                    # DATE and TIMESTAMP columns, but Django wants to see a
                    # python datetime.date, .time, or .datetime.  We use the type
                    # of the Field to determine which to cast to, but it's not
                    # always available.
                    # As a workaround, we cast to date if all the time-related
                    # values are 0, or to time if the date is 1/1/1900.
                    # This could be cleaned a bit by adding a method to the Field
                    # classes to normalize values from the database (the to_python
                    # method is used for validation and isn't what we want here).
                    elif isinstance(value, Database.Timestamp):
                        # In Python 2.3, the cx_Oracle driver returns its own
                        # Timestamp object that we must convert to a datetime class.
                        if not isinstance(value, datetime.datetime):
                            value = datetime.datetime(value.year, value.month, value.day, value.hour,
                                                      value.minute, value.second, value.fsecond)
                        if isinstance(field, DateTimeField):
                            pass  # DateTimeField subclasses DateField so must be checked first.
                        elif isinstance(field, DateField):
                            value = value.date()
                        elif isinstance(field, TimeField) or (value.year == 1900 and value.month == value.day == 1):
                            value = value.time()
                        elif value.hour == value.minute == value.second == value.microsecond == 0:
                            value = value.date()
                    values.append(value)
                return values

            def as_sql(self, with_limits=True):
                """
                Creates the SQL for this query. Returns the SQL string and list
                of parameters.  This is overriden from the original Query class
                to accommodate Oracle's limit/offset SQL.

                If 'with_limits' is False, any limit/offset information is not
                included in the query.
                """
                # The `do_offset` flag indicates whether we need to construct
                # the SQL needed to use limit/offset w/Oracle.
                do_offset = with_limits and (self.high_mark or self.low_mark)

                # If no offsets, just return the result of the base class
                # `as_sql`.
                if not do_offset:
                    return super(OracleQuery, self).as_sql(with_limits=False)

                # `get_columns` needs to be called before `get_ordering` to
                # populate `_select_alias`.
                self.pre_sql_setup()
                out_cols = self.get_columns()
                ordering = self.get_ordering()

                # Getting the "ORDER BY" SQL for the ROW_NUMBER() result.
                if ordering:
                    rn_orderby = ', '.join(ordering)
                else:
                    # Oracle's ROW_NUMBER() function always requires an
                    # order-by clause.  So we need to define a default
                    # order-by, since none was provided.
                    qn = self.quote_name_unless_alias
                    opts = self.model._meta
                    rn_orderby = '%s.%s' % (qn(opts.db_table), qn(opts.fields[0].db_column or opts.fields[0].column))

                # Getting the selection SQL and the params, which has the `rn`
                # extra selection SQL; we pop `rn` after this completes so we do
                # not get the attribute on the returned models.
                self.extra_select['rn'] = 'ROW_NUMBER() OVER (ORDER BY %s )' % rn_orderby
                sql, params= super(OracleQuery, self).as_sql(with_limits=False)
                self.extra_select.pop('rn')

                # Constructing the result SQL, using the initial select SQL
                # obtained above.
                result = ['SELECT * FROM (%s)' % sql]

                # Place WHERE condition on `rn` for the desired range.
                result.append('WHERE rn > %d' % self.low_mark)
                if self.high_mark:
                    result.append('AND rn <= %d' % self.high_mark)

                # Returning the SQL w/params.
                return ' '.join(result), params

        from django.db import connection
        class OracleQuerySet(DefaultQuerySet):
            "The OracleQuerySet is overriden to use OracleQuery."
            def __init__(self, model=None, query=None):
                super(OracleQuerySet, self).__init__(model=model, query=query)
                self.query = query or OracleQuery(self.model, connection)
        return OracleQuerySet

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
            match_option = 'c'
        else:
            match_option = 'i'
        return 'REGEXP_LIKE(%%s %%s %s)' % match_option

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
                table_name = sequence_info['table']
                seq_name = get_sequence_name(table_name)
                column_name = self.quote_name(sequence_info['column'] or 'id')
                query = _get_sequence_reset_sql() % {'sequence': seq_name,
                                                     'table': self.quote_name(table_name),
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
            for f in model._meta.fields:
                if isinstance(f, models.AutoField):
                    sequence_name = get_sequence_name(model._meta.db_table)
                    column_name = self.quote_name(f.db_column or f.name)
                    output.append(query % {'sequence': sequence_name,
                                           'table': model._meta.db_table,
                                           'column': column_name})
                    break # Only one AutoField is allowed per model, so don't bother continuing.
            for f in model._meta.many_to_many:
                sequence_name = get_sequence_name(f.m2m_db_table())
                output.append(query % {'sequence': sequence_name,
                                       'table': f.m2m_db_table(),
                                       'column': self.quote_name('id')})
        return output

    def start_transaction_sql(self):
        return ''

    def tablespace_sql(self, tablespace, inline=False):
        return "%sTABLESPACE %s" % ((inline and "USING INDEX " or ""), self.quote_name(tablespace))

class DatabaseWrapper(BaseDatabaseWrapper):
    features = DatabaseFeatures()
    ops = DatabaseOperations()
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
        if isinstance(params, dict):
            result = {}
            charset = self.charset
            for key, value in params.items():
                result[smart_str(key, charset)] = smart_str(value, charset)
            return result
        else:
            return tuple([smart_str(p, self.charset, True) for p in params])

    def _guess_input_sizes(self, params_list):
        # Mark any string parameter greater than 4000 characters as an NCLOB.
        if isinstance(params_list[0], dict):
            sizes = {}
            iterators = [params.iteritems() for params in params_list]
        else:
            sizes = [None] * len(params_list[0])
            iterators = [enumerate(params) for params in params_list]
        for iterator in iterators:
            for key, value in iterator:
                if isinstance(value, basestring) and len(value) > 4000:
                    sizes[key] = Database.NCLOB
        if isinstance(sizes, dict):
            self.setinputsizes(**sizes)
        else:
            self.setinputsizes(*sizes)

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
        return Database.Cursor.execute(self, query, params)

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
        new_param_list = [self._format_params(i) for i in params]
        self._guess_input_sizes(new_param_list)
        return Database.Cursor.executemany(self, query, new_param_list)

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
            SELECT %(sequence)s.nextval INTO cval FROM dual;
            cval := startvalue - cval;
            IF cval != 0 THEN
                EXECUTE IMMEDIATE 'ALTER SEQUENCE %(sequence)s MINVALUE 0 INCREMENT BY '||cval;
                SELECT %(sequence)s.nextval INTO cval FROM dual;
                EXECUTE IMMEDIATE 'ALTER SEQUENCE %(sequence)s INCREMENT BY 1';
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
