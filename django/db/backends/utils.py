import datetime
import decimal
import functools
import hashlib
import logging
import time
from contextlib import contextmanager

from django.db import NotSupportedError

logger = logging.getLogger('django.db.backends')


class CursorWrapper:
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db

    WRAP_ERROR_ATTRS = frozenset(['fetchone', 'fetchmany', 'fetchall', 'nextset'])

    def __getattr__(self, attr):
        cursor_attr = getattr(self.cursor, attr)
        if attr in CursorWrapper.WRAP_ERROR_ATTRS:
            return self.db.wrap_database_errors(cursor_attr)
        else:
            return cursor_attr

    def __iter__(self):
        with self.db.wrap_database_errors:
            yield from self.cursor

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # Close instead of passing through to avoid backend-specific behavior
        # (#17671). Catch errors liberally because errors in cleanup code
        # aren't useful.
        try:
            self.close()
        except self.db.Database.Error:
            pass

    # The following methods cannot be implemented in __getattr__, because the
    # code must run when the method is invoked, not just when it is accessed.

    def callproc(self, procname, params=None, kparams=None):
        # Keyword parameters for callproc aren't supported in PEP 249, but the
        # database driver may support them (e.g. cx_Oracle).
        if kparams is not None and not self.db.features.supports_callproc_kwargs:
            raise NotSupportedError(
                'Keyword parameters for callproc are not supported on this '
                'database backend.'
            )
        self.db.validate_no_broken_transaction()
        with self.db.wrap_database_errors:
            if params is None and kparams is None:
                return self.cursor.callproc(procname)
            elif kparams is None:
                return self.cursor.callproc(procname, params)
            else:
                params = params or ()
                return self.cursor.callproc(procname, params, kparams)

    def execute(self, sql, params=None):
        return self._execute_with_wrappers(sql, params, many=False, executor=self._execute)

    def executemany(self, sql, param_list):
        return self._execute_with_wrappers(sql, param_list, many=True, executor=self._executemany)

    def _execute_with_wrappers(self, sql, params, many, executor):
        context = {'connection': self.db, 'cursor': self}
        for wrapper in reversed(self.db.execute_wrappers):
            executor = functools.partial(wrapper, executor)
        return executor(sql, params, many, context)

    def _execute(self, sql, params, *ignored_wrapper_args):
        self.db.validate_no_broken_transaction()
        with self.db.wrap_database_errors:
            if params is None:
                # params default might be backend specific.
                return self.cursor.execute(sql)
            else:
                return self.cursor.execute(sql, params)

    def _executemany(self, sql, param_list, *ignored_wrapper_args):
        self.db.validate_no_broken_transaction()
        with self.db.wrap_database_errors:
            return self.cursor.executemany(sql, param_list)


class CursorDebugWrapper(CursorWrapper):

    # XXX callproc isn't instrumented at this time.

    def execute(self, sql, params=None):
        with self.debug_sql(sql, params, use_last_executed_query=True):
            return super().execute(sql, params)

    def executemany(self, sql, param_list):
        with self.debug_sql(sql, param_list, many=True):
            return super().executemany(sql, param_list)

    @contextmanager
    def debug_sql(self, sql=None, params=None, use_last_executed_query=False, many=False):
        start = time.monotonic()
        try:
            yield
        finally:
            stop = time.monotonic()
            duration = stop - start
            if use_last_executed_query:
                sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            try:
                times = len(params) if many else ''
            except TypeError:
                # params could be an iterator.
                times = '?'
            self.db.queries_log.append({
                'sql': '%s times: %s' % (times, sql) if many else sql,
                'time': '%.3f' % duration,
            })
            logger.debug(
                '(%.3f) %s; args=%s',
                duration,
                sql,
                params,
                extra={'duration': duration, 'sql': sql, 'params': params},
            )


###############################################
# Converters from database (string) to Python #
###############################################

def typecast_date(s):
    return datetime.date(*map(int, s.split('-'))) if s else None  # return None if s is null


def typecast_time(s):  # does NOT store time zone information
    if not s:
        return None
    hour, minutes, seconds = s.split(':')
    if '.' in seconds:  # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.time(int(hour), int(minutes), int(seconds), int((microseconds + '000000')[:6]))


def typecast_timestamp(s):  # does NOT store time zone information
    # "2005-07-29 15:48:00.590358-05"
    # "2005-07-29 09:56:00-05"
    if not s:
        return None
    if ' ' not in s:
        return typecast_date(s)
    d, t = s.split()
    # Remove timezone information.
    if '-' in t:
        t, _ = t.split('-', 1)
    elif '+' in t:
        t, _ = t.split('+', 1)
    dates = d.split('-')
    times = t.split(':')
    seconds = times[2]
    if '.' in seconds:  # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.datetime(
        int(dates[0]), int(dates[1]), int(dates[2]),
        int(times[0]), int(times[1]), int(seconds),
        int((microseconds + '000000')[:6])
    )


###############################################
# Converters from Python to database (string) #
###############################################

def split_identifier(identifier):
    """
    Split an SQL identifier into a two element tuple of (namespace, name).

    The identifier could be a table, column, or sequence name might be prefixed
    by a namespace.
    """
    try:
        namespace, name = identifier.split('"."')
    except ValueError:
        namespace, name = '', identifier
    return namespace.strip('"'), name.strip('"')


def truncate_name(identifier, length=None, hash_len=4):
    """
    Shorten an SQL identifier to a repeatable mangled version with the given
    length.

    If a quote stripped name contains a namespace, e.g. USERNAME"."TABLE,
    truncate the table portion only.
    """
    namespace, name = split_identifier(identifier)

    if length is None or len(name) <= length:
        return identifier

    digest = names_digest(name, length=hash_len)
    return '%s%s%s' % ('%s"."' % namespace if namespace else '', name[:length - hash_len], digest)


def names_digest(*args, length):
    """
    Generate a 32-bit digest of a set of arguments that can be used to shorten
    identifying names.
    """
    h = hashlib.md5()
    for arg in args:
        h.update(arg.encode())
    return h.hexdigest()[:length]


def format_number(value, max_digits, decimal_places):
    """
    Format a number into a string with the requisite number of digits and
    decimal places.
    """
    if value is None:
        return None
    context = decimal.getcontext().copy()
    if max_digits is not None:
        context.prec = max_digits
    if decimal_places is not None:
        value = value.quantize(decimal.Decimal(1).scaleb(-decimal_places), context=context)
    else:
        context.traps[decimal.Rounded] = 1
        value = context.create_decimal(value)
    return "{:f}".format(value)


def strip_quotes(table_name):
    """
    Strip quotes off of quoted table names to make them safe for use in index
    names, sequence names, etc. For example '"USER"."TABLE"' (an Oracle naming
    scheme) becomes 'USER"."TABLE'.
    """
    has_quotes = table_name.startswith('"') and table_name.endswith('"')
    return table_name[1:-1] if has_quotes else table_name
