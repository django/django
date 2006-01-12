"""
Caching framework.

This module defines set of cache backends that all conform to a simple API.
In a nutshell, a cache is a set of values -- which can be any object that
may be pickled -- identified by string keys.  For the complete API, see
the abstract Cache object, below.

Client code should not access a cache backend directly; instead
it should use the get_cache() function.  This function will look at
settings.CACHE_BACKEND and use that to create and load a cache object.

The CACHE_BACKEND setting is a quasi-URI; examples are:

    memcached://127.0.0.1:11211/    A memcached backend; the server is running
                                    on localhost port 11211.  You can use
                                    multiple memcached servers by separating
                                    them with semicolons.

    db://tablename/                 A database backend in a table named
                                    "tablename". This table should be created
                                    with "django-admin createcachetable".

    file:///var/tmp/django_cache/   A file-based cache stored in the directory
                                    /var/tmp/django_cache/.

    simple:///                      A simple single-process memory cache; you
                                    probably don't want to use this except for
                                    testing. Note that this cache backend is
                                    NOT threadsafe!

    locmem:///                      A more sophisticated local memory cache;
                                    this is multi-process- and thread-safe.

    dummy:///                       Doesn't actually cache. For use in test
                                    environments.

All caches may take arguments; these are given in query-string style.  Valid
arguments are:

    timeout
        Default timeout, in seconds, to use for the cache.  Defaults
        to 5 minutes (300 seconds).

    max_entries
        For the simple, file, and database backends, the maximum number of
        entries allowed in the cache before it is cleaned.  Defaults to
        300.

    cull_percentage
        The percentage of entries that are culled when max_entries is reached.
        The actual percentage is 1/cull_percentage, so set cull_percentage=3 to
        cull 1/3 of the entries when max_entries is reached.

        A value of 0 for cull_percentage means that the entire cache will be
        dumped when max_entries is reached.  This makes culling *much* faster
        at the expense of more cache misses.

For example:

    memcached://127.0.0.1:11211/?timeout=60
    db://tablename/?timeout=120&max_entries=500&cull_percentage=4

Invalid arguments are silently ignored, as are invalid values of known
arguments.
"""

##############
# Exceptions #
##############

class InvalidCacheBackendError(Exception):
    pass

################################
# Abstract base implementation #
################################

class _Cache:
    def __init__(self, params):
        timeout = params.get('timeout', 300)
        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            timeout = 300
        self.default_timeout = timeout

    def get(self, key, default=None):
        '''
        Fetch a given key from the cache.  If the key does not exist, return
        default, which itself defaults to None.
        '''
        raise NotImplementedError

    def set(self, key, value, timeout=None):
        '''
        Set a value in the cache.  If timeout is given, that timeout will be
        used for the key; otherwise the default cache timeout will be used.
        '''
        raise NotImplementedError

    def delete(self, key):
        '''
        Delete a key from the cache, failing silently.
        '''
        raise NotImplementedError

    def get_many(self, keys):
        '''
        Fetch a bunch of keys from the cache.  For certain backends (memcached,
        pgsql) this can be *much* faster when fetching multiple values.

        Returns a dict mapping each key in keys to its value.  If the given
        key is missing, it will be missing from the response dict.
        '''
        d = {}
        for k in keys:
            val = self.get(k)
            if val is not None:
                d[k] = val
        return d

    def has_key(self, key):
        '''
        Returns True if the key is in the cache and has not expired.
        '''
        return self.get(key) is not None

###########################
# memcached cache backend #
###########################

try:
    import memcache
except ImportError:
    _MemcachedCache = None
else:
    class _MemcachedCache(_Cache):
        "Memcached cache backend."
        def __init__(self, server, params):
            _Cache.__init__(self, params)
            self._cache = memcache.Client(server.split(';'))

        def get(self, key, default=None):
            val = self._cache.get(key)
            if val is None:
                return default
            else:
                return val

        def set(self, key, value, timeout=0):
            self._cache.set(key, value, timeout)

        def delete(self, key):
            self._cache.delete(key)

        def get_many(self, keys):
            return self._cache.get_multi(keys)

##################################
# Single-process in-memory cache #
##################################

import time

class _SimpleCache(_Cache):
    "Simple single-process in-memory cache."
    def __init__(self, host, params):
        _Cache.__init__(self, params)
        self._cache = {}
        self._expire_info = {}

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
        now = time.time()
        exp = self._expire_info.get(key)
        if exp is None:
            return default
        elif exp < now:
            del self._cache[key]
            del self._expire_info[key]
            return default
        else:
            return self._cache[key]

    def set(self, key, value, timeout=None):
        if len(self._cache) >= self._max_entries:
            self._cull()
        if timeout is None:
            timeout = self.default_timeout
        self._cache[key] = value
        self._expire_info[key] = time.time() + timeout

    def delete(self, key):
        try:
            del self._cache[key]
        except KeyError:
            pass
        try:
            del self._expire_info[key]
        except KeyError:
            pass

    def has_key(self, key):
        return self._cache.has_key(key)

    def _cull(self):
        if self._cull_frequency == 0:
            self._cache.clear()
            self._expire_info.clear()
        else:
            doomed = [k for (i, k) in enumerate(self._cache) if i % self._cull_frequency == 0]
            for k in doomed:
                self.delete(k)

###############################
# Thread-safe in-memory cache #
###############################

try:
    import cPickle as pickle
except ImportError:
    import pickle
import copy
from django.utils.synch import RWLock

class _LocMemCache(_SimpleCache):
    "Thread-safe in-memory cache."
    def __init__(self, host, params):
        _SimpleCache.__init__(self, host, params)
        self._lock = RWLock()

    def get(self, key, default=None):
        should_delete = False
        self._lock.reader_enters()
        try:
            now = time.time()
            exp = self._expire_info.get(key)
            if exp is None:
                return default
            elif exp < now:
                should_delete = True
            else:
                return copy.deepcopy(self._cache[key])
        finally:
            self._lock.reader_leaves()
        if should_delete:
            self._lock.writer_enters()
            try:
                del self._cache[key]
                del self._expire_info[key]
                return default
            finally:
                self._lock.writer_leaves()

    def set(self, key, value, timeout=None):
        self._lock.writer_enters()
        try:
            _SimpleCache.set(self, key, value, timeout)
        finally:
            self._lock.writer_leaves()

    def delete(self, key):
        self._lock.writer_enters()
        try:
            _SimpleCache.delete(self, key)
        finally:
            self._lock.writer_leaves()

###############
# Dummy cache #
###############

class _DummyCache(_Cache):
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def get_many(self, *args, **kwargs):
        pass

    def has_key(self, *args, **kwargs):
        return False

####################
# File-based cache #
####################

import os
import urllib

class _FileCache(_SimpleCache):
    "File-based cache."
    def __init__(self, dir, params):
        self._dir = dir
        if not os.path.exists(self._dir):
            self._createdir()
        _SimpleCache.__init__(self, dir, params)
        del self._cache
        del self._expire_info

    def get(self, key, default=None):
        fname = self._key_to_file(key)
        try:
            f = open(fname, 'rb')
            exp = pickle.load(f)
            now = time.time()
            if exp < now:
                f.close()
                os.remove(fname)
            else:
                return pickle.load(f)
        except (IOError, OSError, EOFError, pickle.PickleError):
            pass
        return default

    def set(self, key, value, timeout=None):
        fname = self._key_to_file(key)
        if timeout is None:
            timeout = self.default_timeout
        try:
            filelist = os.listdir(self._dir)
        except (IOError, OSError):
            self._createdir()
            filelist = []
        if len(filelist) > self._max_entries:
            self._cull(filelist)
        try:
            f = open(fname, 'wb')
            now = time.time()
            pickle.dump(now + timeout, f, 2)
            pickle.dump(value, f, 2)
        except (IOError, OSError):
            pass

    def delete(self, key):
        try:
            os.remove(self._key_to_file(key))
        except (IOError, OSError):
            pass

    def has_key(self, key):
        return os.path.exists(self._key_to_file(key))

    def _cull(self, filelist):
        if self._cull_frequency == 0:
            doomed = filelist
        else:
            doomed = [k for (i, k) in enumerate(filelist) if i % self._cull_frequency == 0]
        for fname in doomed:
            try:
                os.remove(os.path.join(self._dir, fname))
            except (IOError, OSError):
                pass

    def _createdir(self):
        try:
            os.makedirs(self._dir)
        except OSError:
            raise EnvironmentError, "Cache directory '%s' does not exist and could not be created'" % self._dir

    def _key_to_file(self, key):
        return os.path.join(self._dir, urllib.quote_plus(key))

#############
# SQL cache #
#############

import base64
from django.core.db import db, DatabaseError
from datetime import datetime

class _DBCache(_Cache):
    "SQL cache backend."
    def __init__(self, table, params):
        _Cache.__init__(self, params)
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
        cursor = db.cursor()
        cursor.execute("SELECT cache_key, value, expires FROM %s WHERE cache_key = %%s" % self._table, [key])
        row = cursor.fetchone()
        if row is None:
            return default
        now = datetime.now()
        if row[2] < now:
            cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % self._table, [key])
            db.commit()
            return default
        return pickle.loads(base64.decodestring(row[1]))

    def set(self, key, value, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        cursor = db.cursor()
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
            db.commit()

    def delete(self, key):
        cursor = db.cursor()
        cursor.execute("DELETE FROM %s WHERE cache_key = %%s" % self._table, [key])
        db.commit()

    def has_key(self, key):
        cursor = db.cursor()
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

##########################################
# Read settings and load a cache backend #
##########################################

from cgi import parse_qsl

_BACKENDS = {
    'memcached': _MemcachedCache,
    'simple': _SimpleCache,
    'locmem': _LocMemCache,
    'file': _FileCache,
    'db': _DBCache,
    'dummy': _DummyCache,
}

def get_cache(backend_uri):
    if backend_uri.find(':') == -1:
        raise InvalidCacheBackendError("Backend URI must start with scheme://")
    scheme, rest = backend_uri.split(':', 1)
    if not rest.startswith('//'):
        raise InvalidCacheBackendError("Backend URI must start with scheme://")
    if scheme not in _BACKENDS.keys():
        raise InvalidCacheBackendError("%r is not a valid cache backend" % scheme)

    host = rest[2:]
    qpos = rest.find('?')
    if qpos != -1:
        params = dict(parse_qsl(rest[qpos+1:]))
        host = rest[2:qpos]
    else:
        params = {}
    if host.endswith('/'):
        host = host[:-1]

    return _BACKENDS[scheme](host, params)

from django.conf.settings import CACHE_BACKEND
cache = get_cache(CACHE_BACKEND)
