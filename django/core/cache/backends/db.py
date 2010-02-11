"Database cache backend."

from django.core.cache.backends.base import BaseCache
from django.db import connection, transaction, DatabaseError
import base64, time
from datetime import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle

class CacheClass(BaseCache):
    def __init__(self, table, params):
        BaseCache.__init__(self, params)
        self._table = table
        max_entries = params.get('max_entries', 300)
        try:
            self._max_entries = int(max_entries)
        except (ValueError, TypeError):
            self._max_entries = 300
        cull_frequency = params.get('cull_frequency', 3)
        try:
            self._cull_frequency = int(cull_frequency)
        except (ValueError, TypeError):
            self._cull_frequency = 3

    def get(self, key, default=None):
        cursor = connection.cursor()
        cursor.execute("SELECT cache_key, value, expires FROM %s WHERE cache_key = %%s" % self._table, [key])
        row = cursor.fetchone()
        if row is None:
            return default
        now = datetime.now()
        if row[2] < now:
            cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % self._table, [key])
            transaction.commit_unless_managed()
            return default
        value = connection.ops.process_clob(row[1])
        return pickle.loads(base64.decodestring(value))

    def set(self, key, value, timeout=None):
        self._base_set('set', key, value, timeout)

    def add(self, key, value, timeout=None):
        return self._base_set('add', key, value, timeout)

    def _base_set(self, mode, key, value, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM %s" % self._table)
        num = cursor.fetchone()[0]
        now = datetime.now().replace(microsecond=0)
        exp = datetime.fromtimestamp(time.time() + timeout).replace(microsecond=0)
        if num > self._max_entries:
            self._cull(cursor, now)
        encoded = base64.encodestring(pickle.dumps(value, 2)).strip()
        cursor.execute("SELECT cache_key, expires FROM %s WHERE cache_key = %%s" % self._table, [key])
        try:
            result = cursor.fetchone()
            if result and (mode == 'set' or
                    (mode == 'add' and result[1] < now)):
                cursor.execute("UPDATE %s SET value = %%s, expires = %%s WHERE cache_key = %%s" % self._table, [encoded, str(exp), key])
            else:
                cursor.execute("INSERT INTO %s (cache_key, value, expires) VALUES (%%s, %%s, %%s)" % self._table, [key, encoded, str(exp)])
        except DatabaseError:
            # To be threadsafe, updates/inserts are allowed to fail silently
            transaction.rollback_unless_managed()
            return False
        else:
            transaction.commit_unless_managed()
            return True

    def delete(self, key):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % self._table, [key])
        transaction.commit_unless_managed()

    def has_key(self, key):
        now = datetime.now().replace(microsecond=0)
        cursor = connection.cursor()
        cursor.execute("SELECT cache_key FROM %s WHERE cache_key = %%s and expires > %%s" % self._table, [key, now])
        return cursor.fetchone() is not None

    def _cull(self, cursor, now):
        if self._cull_frequency == 0:
            self.clear()
        else:
            cursor.execute("DELETE FROM %s WHERE expires < %%s" % self._table, [str(now)])
            cursor.execute("SELECT COUNT(*) FROM %s" % self._table)
            num = cursor.fetchone()[0]
            if num > self._max_entries:
                cursor.execute("SELECT cache_key FROM %s ORDER BY cache_key LIMIT 1 OFFSET %%s" % self._table, [num / self._cull_frequency])
                cursor.execute("DELETE FROM %s WHERE cache_key < %%s" % self._table, [cursor.fetchone()[0]])

    def clear(self):
        cursor = connection.cursor()
        cursor.execute('DELETE FROM %s' % self._table)
