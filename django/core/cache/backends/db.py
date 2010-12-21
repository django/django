"Database cache backend."

from django.core.cache.backends.base import BaseCache
from django.db import connections, router, transaction, DatabaseError
import base64, time
from datetime import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle

class Options(object):
    """A class that will quack like a Django model _meta class.

    This allows cache operations to be controlled by the router
    """
    def __init__(self, table):
        self.db_table = table
        self.app_label = 'django_cache'
        self.module_name = 'cacheentry'
        self.verbose_name = 'cache entry'
        self.verbose_name_plural = 'cache entries'
        self.object_name =  'CacheEntry'
        self.abstract = False
        self.managed = True
        self.proxy = False

class BaseDatabaseCache(BaseCache):
    def __init__(self, table, params):
        BaseCache.__init__(self, params)
        self._table = table

        class CacheEntry(object):
            _meta = Options(table)
        self.cache_model_class = CacheEntry

class DatabaseCache(BaseDatabaseCache):
    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        cursor = connections[db].cursor()

        cursor.execute("SELECT cache_key, value, expires FROM %s WHERE cache_key = %%s" % table, [key])
        row = cursor.fetchone()
        if row is None:
            return default
        now = datetime.now()
        if row[2] < now:
            db = router.db_for_write(self.cache_model_class)
            cursor = connections[db].cursor()
            cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % table, [key])
            transaction.commit_unless_managed(using=db)
            return default
        value = connections[db].ops.process_clob(row[1])
        return pickle.loads(base64.decodestring(value))

    def set(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._base_set('set', key, value, timeout)

    def add(self, key, value, timeout=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set('add', key, value, timeout)

    def _base_set(self, mode, key, value, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        cursor = connections[db].cursor()

        cursor.execute("SELECT COUNT(*) FROM %s" % table)
        num = cursor.fetchone()[0]
        now = datetime.now().replace(microsecond=0)
        exp = datetime.fromtimestamp(time.time() + timeout).replace(microsecond=0)
        if num > self._max_entries:
            self._cull(db, cursor, now)
        encoded = base64.encodestring(pickle.dumps(value, 2)).strip()
        cursor.execute("SELECT cache_key, expires FROM %s WHERE cache_key = %%s" % table, [key])
        try:
            result = cursor.fetchone()
            if result and (mode == 'set' or
                    (mode == 'add' and result[1] < now)):
                cursor.execute("UPDATE %s SET value = %%s, expires = %%s WHERE cache_key = %%s" % table,
                               [encoded, connections[db].ops.value_to_db_datetime(exp), key])
            else:
                cursor.execute("INSERT INTO %s (cache_key, value, expires) VALUES (%%s, %%s, %%s)" % table,
                               [key, encoded, connections[db].ops.value_to_db_datetime(exp)])
        except DatabaseError:
            # To be threadsafe, updates/inserts are allowed to fail silently
            transaction.rollback_unless_managed(using=db)
            return False
        else:
            transaction.commit_unless_managed(using=db)
            return True

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        cursor = connections[db].cursor()

        cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % table, [key])
        transaction.commit_unless_managed(using=db)

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        cursor = connections[db].cursor()

        now = datetime.now().replace(microsecond=0)
        cursor.execute("SELECT cache_key FROM %s WHERE cache_key = %%s and expires > %%s" % table,
                       [key, connections[db].ops.value_to_db_datetime(now)])
        return cursor.fetchone() is not None

    def _cull(self, db, cursor, now):
        if self._cull_frequency == 0:
            self.clear()
        else:
            table = connections[db].ops.quote_name(self._table)
            cursor.execute("DELETE FROM %s WHERE expires < %%s" % table,
                           [connections[db].ops.value_to_db_datetime(now)])
            cursor.execute("SELECT COUNT(*) FROM %s" % table)
            num = cursor.fetchone()[0]
            if num > self._max_entries:
                cursor.execute("SELECT cache_key FROM %s ORDER BY cache_key LIMIT 1 OFFSET %%s" % table, [num / self._cull_frequency])
                cursor.execute("DELETE FROM %s WHERE cache_key < %%s" % table, [cursor.fetchone()[0]])

    def clear(self):
        db = router.db_for_write(self.cache_model_class)
        table = connections[db].ops.quote_name(self._table)
        cursor = connections[db].cursor()
        cursor.execute('DELETE FROM %s' % table)

# For backwards compatibility
class CacheClass(DatabaseCache):
    pass
