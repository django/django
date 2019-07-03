"Database cache backend."
import base64
import pickle
from datetime import datetime

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.db import DatabaseError, connections, models, router, transaction
from django.utils import timezone


class Options:
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
        super().__init__(params)
        self._table = table

        class CacheEntry:
            _meta = Options(table)
        self.cache_model_class = CacheEntry


class DatabaseCache(BaseDatabaseCache):

    # This class uses cursors provided by the database connection. This means
    # it reads expiration values as aware or naive datetimes, depending on the
    # value of USE_TZ and whether the database supports time zones. The ORM's
    # conversion and adaptation infrastructure is then used to avoid comparing
    # aware and naive datetimes accidentally.

    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def get(self, key, default=None, version=None):
        return self.get_many([key], version).get(key, default)

    def get_many(self, keys, version=None):
        if not keys:
            return {}

        key_map = {}
        for key in keys:
            self.validate_key(key)
            key_map[self.make_key(key, version)] = key

        db = router.db_for_read(self.cache_model_class)
        connection = connections[db]
        quote_name = connection.ops.quote_name
        table = quote_name(self._table)

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT %s, %s, %s FROM %s WHERE %s IN (%s)' % (
                    quote_name('cache_key'),
                    quote_name('value'),
                    quote_name('expires'),
                    table,
                    quote_name('cache_key'),
                    ', '.join(['%s'] * len(key_map)),
                ),
                list(key_map),
            )
            rows = cursor.fetchall()

        result = {}
        expired_keys = []
        expression = models.Expression(output_field=models.DateTimeField())
        converters = (connection.ops.get_db_converters(expression) + expression.get_db_converters(connection))
        for key, value, expires in rows:
            for converter in converters:
                expires = converter(expires, expression, connection)
            if expires < timezone.now():
                expired_keys.append(key)
            else:
                value = connection.ops.process_clob(value)
                value = pickle.loads(base64.b64decode(value.encode()))
                result[key_map.get(key)] = value
        self._base_delete_many(expired_keys)
        return result

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._base_set('set', key, value, timeout)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set('add', key, value, timeout)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set('touch', key, None, timeout)

    def _base_set(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
        timeout = self.get_backend_timeout(timeout)
        db = router.db_for_write(self.cache_model_class)
        connection = connections[db]
        quote_name = connection.ops.quote_name
        table = quote_name(self._table)

        with connection.cursor() as cursor:
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
            pickled = pickle.dumps(value, self.pickle_protocol)
            # The DB column is expecting a string, so make sure the value is a
            # string, not bytes. Refs #19274.
            b64encoded = base64.b64encode(pickled).decode('latin1')
            try:
                # Note: typecasting for datetimes is needed by some 3rd party
                # database backends. All core backends work without typecasting,
                # so be careful about changes here - test suite will NOT pick
                # regressions.
                with transaction.atomic(using=db):
                    cursor.execute(
                        'SELECT %s, %s FROM %s WHERE %s = %%s' % (
                            quote_name('cache_key'),
                            quote_name('expires'),
                            table,
                            quote_name('cache_key'),
                        ),
                        [key]
                    )
                    result = cursor.fetchone()

                    if result:
                        current_expires = result[1]
                        expression = models.Expression(output_field=models.DateTimeField())
                        for converter in (connection.ops.get_db_converters(expression) +
                                          expression.get_db_converters(connection)):
                            current_expires = converter(current_expires, expression, connection)

                    exp = connection.ops.adapt_datetimefield_value(exp)
                    if result and mode == 'touch':
                        cursor.execute(
                            'UPDATE %s SET %s = %%s WHERE %s = %%s' % (
                                table,
                                quote_name('expires'),
                                quote_name('cache_key')
                            ),
                            [exp, key]
                        )
                    elif result and (mode == 'set' or (mode == 'add' and current_expires < now)):
                        cursor.execute(
                            'UPDATE %s SET %s = %%s, %s = %%s WHERE %s = %%s' % (
                                table,
                                quote_name('value'),
                                quote_name('expires'),
                                quote_name('cache_key'),
                            ),
                            [b64encoded, exp, key]
                        )
                    elif mode != 'touch':
                        cursor.execute(
                            'INSERT INTO %s (%s, %s, %s) VALUES (%%s, %%s, %%s)' % (
                                table,
                                quote_name('cache_key'),
                                quote_name('value'),
                                quote_name('expires'),
                            ),
                            [key, b64encoded, exp]
                        )
                    else:
                        return False  # touch failed.
            except DatabaseError:
                # To be threadsafe, updates/inserts are allowed to fail silently
                return False
            else:
                return True

    def delete(self, key, version=None):
        self.delete_many([key], version)

    def delete_many(self, keys, version=None):
        key_list = []
        for key in keys:
            self.validate_key(key)
            key_list.append(self.make_key(key, version))
        self._base_delete_many(key_list)

    def _base_delete_many(self, keys):
        if not keys:
            return

        db = router.db_for_write(self.cache_model_class)
        connection = connections[db]
        quote_name = connection.ops.quote_name
        table = quote_name(self._table)

        with connection.cursor() as cursor:
            cursor.execute(
                'DELETE FROM %s WHERE %s IN (%s)' % (
                    table,
                    quote_name('cache_key'),
                    ', '.join(['%s'] * len(keys)),
                ),
                keys,
            )

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

        db = router.db_for_read(self.cache_model_class)
        connection = connections[db]
        quote_name = connection.ops.quote_name

        if settings.USE_TZ:
            now = datetime.utcnow()
        else:
            now = datetime.now()
        now = now.replace(microsecond=0)

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT %s FROM %s WHERE %s = %%s and expires > %%s' % (
                    quote_name('cache_key'),
                    quote_name(self._table),
                    quote_name('cache_key'),
                ),
                [key, connection.ops.adapt_datetimefield_value(now)]
            )
            return cursor.fetchone() is not None

    def _cull(self, db, cursor, now):
        if self._cull_frequency == 0:
            self.clear()
        else:
            connection = connections[db]
            table = connection.ops.quote_name(self._table)
            cursor.execute("DELETE FROM %s WHERE expires < %%s" % table,
                           [connection.ops.adapt_datetimefield_value(now)])
            cursor.execute("SELECT COUNT(*) FROM %s" % table)
            num = cursor.fetchone()[0]
            if num > self._max_entries:
                cull_num = num // self._cull_frequency
                cursor.execute(
                    connection.ops.cache_key_culling_sql() % table,
                    [cull_num])
                cursor.execute("DELETE FROM %s "
                               "WHERE cache_key < %%s" % table,
                               [cursor.fetchone()[0]])

    def clear(self):
        db = router.db_for_write(self.cache_model_class)
        connection = connections[db]
        table = connection.ops.quote_name(self._table)
        with connection.cursor() as cursor:
            cursor.execute('DELETE FROM %s' % table)
