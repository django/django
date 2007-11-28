"Thread-safe in-memory cache backend."

import time
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.core.cache.backends.simple import CacheClass as SimpleCacheClass
from django.utils.synch import RWLock

class CacheClass(SimpleCacheClass):
    def __init__(self, host, params):
        SimpleCacheClass.__init__(self, host, params)
        self._lock = RWLock()

    def add(self, key, value, timeout=None):
        self._lock.writer_enters()
        # Python 2.3 and 2.4 don't allow combined try-except-finally blocks.
        try:
            try:
                super(CacheClass, self).add(key, pickle.dumps(value), timeout)
            except pickle.PickleError:
                pass
        finally:
            self._lock.writer_leaves()

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
                try:
                    return pickle.loads(self._cache[key])
                except pickle.PickleError:
                    return default
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
        # Python 2.3 and 2.4 don't allow combined try-except-finally blocks.
        try:
            try:
                super(CacheClass, self).set(key, pickle.dumps(value), timeout)
            except pickle.PickleError:
                pass
        finally:
            self._lock.writer_leaves()

    def delete(self, key):
        self._lock.writer_enters()
        try:
            SimpleCacheClass.delete(self, key)
        finally:
            self._lock.writer_leaves()
