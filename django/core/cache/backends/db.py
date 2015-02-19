"Database cache backend."
import base64
from datetime import datetime

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.db import DatabaseError, connections, router, transaction
from django.db.backends.utils import typecast_timestamp
from django.utils import six, timezone
from django.utils.encoding import force_bytes

try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:
    import pickle


class Options(object):
    """A class that will quack like a Django model _meta class.

    This allows cache operations to be controlled by the router
    """
    def __init__(self, table):
        self.db_table = table
        self.app_label = 'django_cache'
        self.model_name = 'cacheentry'
        self.verbose_name = 'cache entry'
        self.verbose_name_plural = 'cache entries'
        self.object_name = 'CacheEntry'
        self.abstract = False
        self.managed = True
        self.proxy = False
        self.swapped = False


class BaseDatabaseCache(BaseCache):
    def __init__(self, table, params):
        BaseCache.__init__(self, params)
        self._table = table

        class CacheEntry(object):
            _meta = Options(table)
        self.cache_model_class = CacheEntry


class DatabaseCache(BaseDatabaseCache):

    # This class uses cursors provided by the database connection. This means
    # it reads expiration values as aware or naive datetimes depending on the
    # value of USE_TZ. They must be compared to aware or naive representations
    # of "now" respectively.

    # But it bypasses the ORM for write operations. As a consequence, aware
    # datetimes aren't made naive for databases that don't support time zones.
    # We work around this problem by always using naive datetimes when writing
    # expiration values, in UTC when USE_TZ = True and in local time otherwise.

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute("SELECT cache_key, value, expires FROM %s "
                           "WHERE cache_key = %%s" % table, [key])
            row = cursor.fetchone()
        if row is None:
            return default
        now = timezone.now()
        expires = row[2]
        if connections[db].features.needs_datetime_string_cast and not isinstance(expires, datetime):
            # Note: typecasting is needed by some 3rd party database backends.
            # All core backends work without typecasting, so be careful about
            # changes here - test suite will NOT pick regressions here.
            expires = typecast_timestamp(str(expires))
        if expires < now:
            db = router.db_for_write(self.cache_model_class)
            with connections[db].cursor() as cursor:
                cursor.execute("DELETE FROM %s "
                               "WHERE cache_key = %%s" % table, [key])
            return default
        value = connections[db].ops.process_clob(row[1])
        return pickle.loads(base64.b64decode(force_bytes(value)))

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._base_set('set', key, value, timeout)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set('add', key, value, timeout)

    def _base_set(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
        timeout = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM %s" % table)
            num = cursor.fetchone()[0]
            now = timezone.now()
            now = now.replace(microsecond=0)
            if timeout is None:
                exp = datetime.max
            elif settings.USE_TZ:
                exp = datetime.utcfromtimestamp(timeout)
            else:
                exp = datetime.fromtimestamp(timeout)
            exp = exp.replace(microsecond=0)
            if num > self._max_entries:
                self._cull(db, cursor, now)
            pickled = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
            b64encoded = base64.b64encode(pickled)
            # The DB column is expecting a string, so make sure the value is a
            # string, not bytes. Refs #19274.
            if six.PY3:
                b64encoded = b64encoded.decode('latin1')
            try:
                # Note: typecasting for datetimes is needed by some 3rd party
                # database backends. All core backends work without typecasting,
                # so be careful about changes here - test suite will NOT pick
                # regressions.
                with transaction.atomic(using=db):
                    cursor.execute("SELECT cache_key, expires FROM %s "
                                   "WHERE cache_key = %%s" % table, [key])
                    result = cursor.fetchone()
                    if result:
                        current_expires = result[1]
                        if (connections[db].features.needs_datetime_string_cast and not
                                isinstance(current_expires, datetime)):
                            current_expires = typecast_timestamp(str(current_expires))
                    exp = connections[db].ops.value_to_db_datetime(exp)
                    if result and (mode == 'set' or (mode == 'add' and current_expires < now)):
                        cursor.execute("UPDATE %s SET value = %%s, expires = %%s "
                                       "WHERE cache_key = %%s" % table,
                                       [b64encoded, exp, key])
                    else:
                        cursor.execute("INSERT INTO %s (cache_key, value, expires) "
                                       "VALUES (%%s, %%s, %%s)" % table,
                                       [key, b64encoded, exp])
            except DatabaseError:
                # To be threadsafe, updates/inserts are allowed to fail silently
                return False
            else:
                return True

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        with connections[db].cursor() as cursor:
            cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % table, [key])

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)

        if settings.USE_TZ:
            now = datetime.utcnow()
        else:
            now = datetime.now()
        now = now.replace(microsecond=0)

        with connections[db].cursor() as cursor:
            cursor.execute("SELECT cache_key FROM %s "
                           "WHERE cache_key = %%s and expires > %%s" % table,
                           [key, connections[db].ops.value_to_db_datetime(now)])
            return cursor.fetchone() is not None

    def _cull(self, db, cursor, now):
        if self._cull_frequency == 0:
            self.clear()
        else:
            # When USE_TZ is True, 'now' will be an aware datetime in UTC.
            now = now.replace(tzinfo=None)
            table = connections[db].ops.quote_name(self._table)
            cursor.execute("DELETE FROM %s WHERE expires < %%s" % table,
                           [connections[db].ops.value_to_db_datetime(now)])
            cursor.execute("SELECT COUNT(*) FROM %s" % table)
            num = cursor.fetchone()[0]
            if num > self._max_entries:
                cull_num = num // self._cull_frequency
                cursor.execute(
                    connections[db].ops.cache_key_culling_sql() % table,
                    [cull_num])
                cursor.execute("DELETE FROM %s "
                               "WHERE cache_key < %%s" % table,
                               [cursor.fetchone()[0]])

    def clear(self):
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        with connections[db].cursor() as cursor:
            cursor.execute('DELETE FROM %s' % table)
