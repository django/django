"Database cache backend."

from django.core.cache.backends.base import BaseCache
from django.db import connection, transaction
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
        return pickle.loads(base64.decodestring(row[1]))

    def set(self, key, value, timeout=None):
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
        cursor.execute("SELECT cache_key FROM %s WHERE cache_key = %%s" % self._table, [key])
        try:
            if cursor.fetchone():
                cursor.execute("UPDATE %s SET value = %%s, expires = %%s WHERE cache_key = %%s" % self._table, [encoded, str(exp), key])
            else:
                cursor.execute("INSERT INTO %s (cache_key, value, expires) VALUES (%%s, %%s, %%s)" % self._table, [key, encoded, str(exp)])
        except DatabaseError:
            # To be threadsafe, updates/inserts are allowed to fail silently
            pass
        else:
            transaction.commit_unless_managed()

    def delete(self, key):
        cursor = connection.cursor()
        cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % self._table, [key])
        transaction.commit_unless_managed()

    def has_key(self, key):
        cursor = connection.cursor()
        cursor.execute("SELECT cache_key FROM %s WHERE cache_key = %%s" % self._table, [key])
        return cursor.fetchone() is not None

    def _cull(self, cursor, now):
        if self._cull_frequency == 0:
            cursor.execute("DELETE FROM %s" % self._table)
        else:
            cursor.execute("DELETE FROM %s WHERE expires < %%s" % self._table, [str(now)])
            cursor.execute("SELECT COUNT(*) FROM %s" % self._table)
            num = cursor.fetchone()[0]
            if num > self._max_entries:
                cursor.execute("SELECT cache_key FROM %s ORDER BY cache_key LIMIT 1 OFFSET %%s" % self._table, [num / self._cull_frequency])
                cursor.execute("DELETE FROM %s WHERE cache_key < %%s" % self._table, [cursor.fetchone()[0]])
