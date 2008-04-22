"""
Oracle database backend for Django.

Requires cx_Oracle: http://www.python.net/crew/atuining/cx_Oracle/
"""

from django.db.backends import BaseDatabaseWrapper, BaseDatabaseFeatures, BaseDatabaseOperations, util
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_str, force_unicode
import datetime
import os

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

    def max_name_length(self):
        return 30

    def query_set_class(self, DefaultQuerySet):
        from django.db import connection
        from django.db.models.query import EmptyResultSet, GET_ITERATOR_CHUNK_SIZE, quote_only_if_word

        class OracleQuerySet(DefaultQuerySet):

            def iterator(self):
                "Performs the SELECT database lookup of this QuerySet."

                from django.db.models.query import get_cached_row

                # self._select is a dictionary, and dictionaries' key order is
                # undefined, so we convert it to a list of tuples.
                extra_select = self._select.items()

                full_query = None

                try:
                    try:
                        select, sql, params, full_query = self._get_sql_clause(get_full_query=True)
                    except TypeError:
                        select, sql, params = self._get_sql_clause()
                except EmptyResultSet:
                    raise StopIteration
                if not full_query:
                    full_query = "SELECT %s%s\n%s" % ((self._distinct and "DISTINCT " or ""), ', '.join(select), sql)

                cursor = connection.cursor()
                cursor.execute(full_query, params)

                fill_cache = self._select_related
                fields = self.model._meta.fields
                index_end = len(fields)

                # so here's the logic;
                # 1. retrieve each row in turn
                # 2. convert NCLOBs

                while 1:
                    rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
                    if not rows:
                        raise StopIteration
                    for row in rows:
                        row = self.resolve_columns(row, fields)
                        if fill_cache:
                            obj, index_end = get_cached_row(klass=self.model, row=row,
                                                            index_start=0, max_depth=self._max_related_depth)
                        else:
                            obj = self.model(*row[:index_end])
                        for i, k in enumerate(extra_select):
                            setattr(obj, k[0], row[index_end+i])
                        yield obj


            def _get_sql_clause(self, get_full_query=False):
                from django.db.models.query import fill_table_cache, \
                    handle_legacy_orderlist, orderfield2column

                opts = self.model._meta
                qn = connection.ops.quote_name

                # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
                select = ["%s.%s" % (qn(opts.db_table), qn(f.column)) for f in opts.fields]
                tables = [quote_only_if_word(t) for t in self._tables]
                joins = SortedDict()
                where = self._where[:]
                params = self._params[:]

                # Convert self._filters into SQL.
                joins2, where2, params2 = self._filters.get_sql(opts)
                joins.update(joins2)
                where.extend(where2)
                params.extend(params2)

                # Add additional tables and WHERE clauses based on select_related.
                if self._select_related:
                    fill_table_cache(opts, select, tables, where, opts.db_table, [opts.db_table])

                # Add any additional SELECTs.
                if self._select:
                    select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), qn(s[0])) for s in self._select.items()])

                # Start composing the body of the SQL statement.
                sql = [" FROM", qn(opts.db_table)]

                # Compose the join dictionary into SQL describing the joins.
                if joins:
                    sql.append(" ".join(["%s %s %s ON %s" % (join_type, table, alias, condition)
                                    for (alias, (table, join_type, condition)) in joins.items()]))

                # Compose the tables clause into SQL.
                if tables:
                    sql.append(", " + ", ".join(tables))

                # Compose the where clause into SQL.
                if where:
                    sql.append(where and "WHERE " + " AND ".join(where))

                # ORDER BY clause
                order_by = []
                if self._order_by is not None:
                    ordering_to_use = self._order_by
                else:
                    ordering_to_use = opts.ordering
                for f in handle_legacy_orderlist(ordering_to_use):
                    if f == '?': # Special case.
                        order_by.append(DatabaseOperations().random_function_sql())
                    else:
                        if f.startswith('-'):
                            col_name = f[1:]
                            order = "DESC"
                        else:
                            col_name = f
                            order = "ASC"
                        if "." in col_name:
                            table_prefix, col_name = col_name.split('.', 1)
                            table_prefix = qn(table_prefix) + '.'
                        else:
                            # Use the database table as a column prefix if it wasn't given,
                            # and if the requested column isn't a custom SELECT.
                            if "." not in col_name and col_name not in (self._select or ()):
                                table_prefix = qn(opts.db_table) + '.'
                            else:
                                table_prefix = ''
                        order_by.append('%s%s %s' % (table_prefix, qn(orderfield2column(col_name, opts)), order))
                if order_by:
                    sql.append("ORDER BY " + ", ".join(order_by))

                # Look for column name collisions in the select elements
                # and fix them with an AS alias.  This allows us to do a
                # SELECT * later in the paging query.
                cols = [clause.split('.')[-1] for clause in select]
                for index, col in enumerate(cols):
                    if cols.count(col) > 1:
                        col = '%s%d' % (col.replace('"', ''), index)
                        cols[index] = col
                        select[index] = '%s AS %s' % (select[index], col)

                # LIMIT and OFFSET clauses
                # To support limits and offsets, Oracle requires some funky rewriting of an otherwise normal looking query.
                select_clause = ",".join(select)
                distinct = (self._distinct and "DISTINCT " or "")

                if order_by:
                    order_by_clause = " OVER (ORDER BY %s )" % (", ".join(order_by))
                else:
                    #Oracle's row_number() function always requires an order-by clause.
                    #So we need to define a default order-by, since none was provided.
                    order_by_clause = " OVER (ORDER BY %s.%s)" % \
                        (qn(opts.db_table), qn(opts.fields[0].db_column or opts.fields[0].column))
                # limit_and_offset_clause
                if self._limit is None:
                    assert self._offset is None, "'offset' is not allowed without 'limit'"

                if self._offset is not None:
                    offset = int(self._offset)
                else:
                    offset = 0
                if self._limit is not None:
                    limit = int(self._limit)
                else:
                    limit = None

                limit_and_offset_clause = ''
                if limit is not None:
                    limit_and_offset_clause = "WHERE rn > %s AND rn <= %s" % (offset, limit+offset)
                elif offset:
                    limit_and_offset_clause = "WHERE rn > %s" % (offset)

                if len(limit_and_offset_clause) > 0:
                    fmt = \
    """SELECT * FROM
      (SELECT %s%s,
              ROW_NUMBER()%s AS rn
       %s)
    %s"""
                    full_query = fmt % (distinct, select_clause,
                                        order_by_clause, ' '.join(sql).strip(),
                                        limit_and_offset_clause)
                else:
                    full_query = None

                if get_full_query:
                    return select, " ".join(sql), params, full_query
                else:
                    return select, " ".join(sql), params

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
