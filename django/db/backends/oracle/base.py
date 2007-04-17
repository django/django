"""
Oracle database backend for Django.

Requires cx_Oracle: http://www.python.net/crew/atuining/cx_Oracle/
"""

from django.conf import settings
from django.db.backends import util
try:
    import cx_Oracle as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading cx_Oracle module: %s" % e
import datetime
from django.utils.datastructures import SortedDict


DatabaseError = Database.Error

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

class DatabaseWrapper(local):
    def __init__(self, **kwargs):
        self.connection = None
        self.queries = []
        self.options = kwargs

    def _valid_connection(self):
        return self.connection is not None

    def cursor(self):
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
        # default arraysize of 1 is highly sub-optimal
        cursor.arraysize = 100
        # set oracle date to ansi date format
        cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD'")
        cursor.execute("ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'")
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

allows_group_by_ordinal = False
allows_unique_and_pk = False        # Suppress UNIQUE/PK for Oracle (ORA-02259)
autoindexes_primary_keys = True
needs_datetime_string_cast = False
needs_upper_for_iops = True
supports_constraints = True
supports_tablespaces = True
uses_case_insensitive_names = True

class FormatStylePlaceholderCursor(Database.Cursor):
    """
    Django uses "format" (e.g. '%s') style placeholders, but Oracle uses ":var" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def _rewrite_args(self, query, params=None):
        if params is None:
            params = []
        else:
            # cx_Oracle can't handle unicode parameters, so cast to str for now
            for i, param in enumerate(params):
                if type(param) == unicode:
                    try:
                        params[i] = param.encode('utf-8')
                    except UnicodeError:
                        params[i] = str(param)
        args = [(':arg%d' % i) for i in range(len(params))]
        query = query % tuple(args)
        # cx_Oracle cannot execute a query with the closing ';'
        if query.endswith(';'):
            query = query[:-1]
        return query, params

    def execute(self, query, params=None):
        query, params = self._rewrite_args(query, params)
        return Database.Cursor.execute(self, query, params)

    def executemany(self, query, params=None):
        query, params = self._rewrite_args(query, params)
        return Database.Cursor.executemany(self, query, params)

def quote_name(name):
    # SQL92 requires delimited (quoted) names to be case-sensitive.  When
    # not quoted, Oracle has case-insensitive behavior for identifiers, but
    # always defaults to uppercase.
    # We simplify things by making Oracle identifiers always uppercase.
    if not name.startswith('"') and not name.endswith('"'):
        name = '"%s"' % util.truncate_name(name.upper(), get_max_name_length())
    return name.upper()

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    sq_name = util.truncate_name(table_name, get_max_name_length()-3)
    cursor.execute('SELECT %s_sq.currval FROM dual' % sq_name)
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://download-east.oracle.com/docs/cd/B10501_01/server.920/a96540/functions42a.htm#1017163
    return "EXTRACT(%s FROM %s)" % (lookup_type, table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # Oracle uses TRUNC() for both dates and numbers.
    # http://download-east.oracle.com/docs/cd/B10501_01/server.920/a96540/functions155a.htm#SQLRF06151
    if lookup_type == 'day':
        sql = 'TRUNC(%s)' % (field_name,)
    else:
        sql = "TRUNC(%s, '%s')" % (field_name, lookup_type)
    return sql

def get_datetime_cast_sql():
    return "TO_TIMESTAMP(%s, 'YYYY-MM-DD HH24:MI:SS')"

def get_limit_offset_sql(limit, offset=None):
    # Limits and offset are too complicated to be handled here.
    # Instead, they are handled in django/db/backends/oracle/query.py.
    return ""

def get_random_function_sql():
    return "DBMS_RANDOM.RANDOM"

def get_deferrable_sql():
    return " DEFERRABLE INITIALLY DEFERRED"

def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return "DROP CONSTRAINT"

def get_pk_default_value():
    return "DEFAULT"

def get_max_name_length():
    return 30

def get_start_transaction_sql():
    return None

def get_tablespace_sql():
    return "TABLESPACE %s"

def get_autoinc_sql(table):
    # To simulate auto-incrementing primary keys in Oracle, we have to
    # create a sequence and a trigger.
    sq_name = get_sequence_name(table)
    tr_name = get_trigger_name(table)
    sequence_sql = 'CREATE SEQUENCE %s;' % sq_name
    trigger_sql = """CREATE OR REPLACE TRIGGER %s
  BEFORE INSERT ON %s
  FOR EACH ROW
  WHEN (new.id IS NULL)
    BEGIN
      SELECT %s.nextval INTO :new.id FROM dual;
    END;\n""" % (tr_name, quote_name(table), sq_name)
    return sequence_sql, trigger_sql

def _get_sequence_reset_sql():
    # TODO: colorize this SQL code with style.SQL_KEYWORD(), etc.
    return """
        DECLARE
            startvalue integer;
            cval integer;
        BEGIN
            LOCK TABLE %(table)s IN SHARE MODE;
            SELECT NVL(MAX(id), 0) INTO startvalue FROM %(table)s;
            SELECT %(sequence)s.nextval INTO cval FROM dual;
            cval := startvalue - cval;
            IF cval != 0 THEN
                EXECUTE IMMEDIATE 'ALTER SEQUENCE %(sequence)s MINVALUE 0 INCREMENT BY '||cval;
                SELECT %(sequence)s.nextval INTO cval FROM dual;
                EXECUTE IMMEDIATE 'ALTER SEQUENCE %(sequence)s INCREMENT BY 1';
            END IF;
            COMMIT;
        END;\n"""

def get_sql_flush(style, tables, sequences):
    """Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state
    """
    # Return a list of 'TRUNCATE x;', 'TRUNCATE y;',
    # 'TRUNCATE z;'... style SQL statements
    if tables:
        # Oracle does support TRUNCATE, but it seems to get us into
        # FK referential trouble, whereas DELETE FROM table works.
        sql = ['%s %s %s;' % \
                (style.SQL_KEYWORD('DELETE'),
                 style.SQL_KEYWORD('FROM'),
                 style.SQL_FIELD(quote_name(table))
                 ) for table in tables]
        # Since we've just deleted all the rows, running our sequence
        # ALTER code will reset the sequence to 0.
        for sequence_info in sequences:
            table_name = sequence_info['table']
            seq_name = get_sequence_name(table_name)
            query = _get_sequence_reset_sql() % {'sequence':seq_name,
                                                 'table':quote_name(table_name)}
            sql.append(query)
        return sql
    else:
        return []

def get_sequence_name(table):
    name_length = get_max_name_length() - 3
    return '%s_SQ' % util.truncate_name(table, name_length).upper()

def get_sql_sequence_reset(style, model_list):
    "Returns a list of the SQL statements to reset sequences for the given models."
    from django.db import models
    output = []
    query = _get_sequence_reset_sql()
    for model in model_list:
        for f in model._meta.fields:
            if isinstance(f, models.AutoField):
                sequence_name = get_sequence_name(model._meta.db_table)
                output.append(query % {'sequence':sequence_name,
                                       'table':model._meta.db_table})
                break # Only one AutoField is allowed per model, so don't bother continuing.
        for f in model._meta.many_to_many:
            sequence_name = get_sequence_name(f.m2m_db_table())
            output.append(query % {'sequence':sequence_name,
                                   'table':f.m2m_db_table()})
    return output

def get_trigger_name(table):
    name_length = get_max_name_length() - 3
    return '%s_TR' % util.truncate_name(table, name_length).upper()

def get_query_set_class(DefaultQuerySet):
    "Create a custom QuerySet class for Oracle."

    from django.db import backend, connection
    from django.db.models.query import EmptyResultSet, GET_ITERATOR_CHUNK_SIZE

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
                full_query = "SELECT %s%s\n%s" % \
                             ((self._distinct and "DISTINCT " or ""),
                              ', '.join(select), sql)

            cursor = connection.cursor()
            cursor.execute(full_query, params)

            fill_cache = self._select_related
            index_end = len(self.model._meta.fields)

            # so here's the logic;
            # 1. retrieve each row in turn
            # 2. convert NCLOBs

            while 1:
                rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
                if not rows:
                    raise StopIteration
                for row in rows:
                    row = self.resolve_columns(row)
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

            # Construct the fundamental parts of the query: SELECT X FROM Y WHERE Z.
            select = ["%s.%s" % (backend.quote_name(opts.db_table), backend.quote_name(f.column)) for f in opts.fields]
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
                select.extend(['(%s) AS %s' % (quote_only_if_word(s[1]), backend.quote_name(s[0])) for s in self._select.items()])

            # Start composing the body of the SQL statement.
            sql = [" FROM", backend.quote_name(opts.db_table)]

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
                    order_by.append(backend.get_random_function_sql())
                else:
                    if f.startswith('-'):
                        col_name = f[1:]
                        order = "DESC"
                    else:
                        col_name = f
                        order = "ASC"
                    if "." in col_name:
                        table_prefix, col_name = col_name.split('.', 1)
                        table_prefix = backend.quote_name(table_prefix) + '.'
                    else:
                        # Use the database table as a column prefix if it wasn't given,
                        # and if the requested column isn't a custom SELECT.
                        if "." not in col_name and col_name not in (self._select or ()):
                            table_prefix = backend.quote_name(opts.db_table) + '.'
                        else:
                            table_prefix = ''
                    order_by.append('%s%s %s' % (table_prefix, backend.quote_name(orderfield2column(col_name, opts)), order))
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
                    (backend.quote_name(opts.db_table),
                    backend.quote_name(opts.fields[0].db_column or opts.fields[0].column))
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
            from django.db.models.fields import DateField, DateTimeField, TimeField
            values = []
            for value, field in map(None, row, fields):
                if isinstance(value, Database.LOB):
                    value = value.read()
                # Since Oracle won't distinguish between NULL and an empty
                # string (''), we store empty strings as a space.  Here is
                # where we undo that treachery.
                if value == ' ':
                    value = ''
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
                    elif isinstance(field, TimeField):
                        value = value.time()
                    elif value.hour == value.minute == value.second == value.microsecond == 0:
                        value = value.date()
                    elif value.year == 1900 and value.month == value.day == 1:
                        value = value.time()
                values.append(value)
            return values

    return OracleQuerySet


OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': '= UPPER(%s)',
    'contains': "LIKE %s ESCAPE '\\'",
    'icontains': "LIKE UPPER(%s) ESCAPE '\\'",
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': "LIKE %s ESCAPE '\\'",
    'endswith': "LIKE %s ESCAPE '\\'",
    'istartswith': "LIKE UPPER(%s) ESCAPE '\\'",
    'iendswith': "LIKE UPPER(%s) ESCAPE '\\'",
}
