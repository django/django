"Thread-safe in-memory cache backend."

from django.core.cache.backends.simple import CacheClass as SimpleCacheClass
from django.utils.synch import RWLock
import copy, time
try:
    import cPickle as pickle
except ImportError:
    import pickle

class CacheClass(SimpleCacheClass):
    def __init__(self, host, params):
        SimpleCacheClass.__init__(self, host, params)
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
            SimpleCacheClass.set(self, key, value, timeout)
        finally:
            self._lock.writer_leaves()

    def delete(self, key):
        self._lock.writer_enters()
        try:
            SimpleCacheClass.delete(self, key)
        finally:
            self._lock.writer_leaves()
