"Thread-safe in-memory cache backend."
import pickle
import time
from contextlib import contextmanager, suppress

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils.synch import RWLock

# Global in-memory store of cache data. Keyed by name, to provide
# multiple named local memory caches.
_caches = {}
_expire_info = {}
_locks = {}


@contextmanager
def dummy():
    """A context manager that does nothing special."""
    yield


class LocMemCache(BaseCache):
    def __init__(self, name, params):
        BaseCache.__init__(self, params)
        self._cache = _caches.setdefault(name, {})
        self._expire_info = _expire_info.setdefault(name, {})
        self._lock = _locks.setdefault(name, RWLock())

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        pickled = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        with self._lock.writer():
            if self._has_expired(key):
                self._set(key, pickled, timeout)
                return True
            return False

    def get(self, key, default=None, version=None, acquire_lock=True):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        pickled = None
        with (self._lock.reader() if acquire_lock else dummy()):
            if not self._has_expired(key):
                pickled = self._cache[key]
        if pickled is not None:
            try:
                return pickle.loads(pickled)
            except pickle.PickleError:
                return default

        with (self._lock.writer() if acquire_lock else dummy()):
            with suppress(KeyError):
                del self._cache[key]
                del self._expire_info[key]
            return default

    def _set(self, key, value, timeout=DEFAULT_TIMEOUT):
        if len(self._cache) >= self._max_entries:
            self._cull()
        self._cache[key] = value
        self._expire_info[key] = self.get_backend_timeout(timeout)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        pickled = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
        with self._lock.writer():
            self._set(key, pickled, timeout)

    def incr(self, key, delta=1, version=None):
        with self._lock.writer():
            value = self.get(key, version=version, acquire_lock=False)
            if value is None:
                raise ValueError("Key '%s' not found" % key)
            new_value = value + delta
            key = self.make_key(key, version=version)
            pickled = pickle.dumps(new_value, pickle.HIGHEST_PROTOCOL)
            self._cache[key] = pickled
        return new_value

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        with self._lock.reader():
            if not self._has_expired(key):
                return True

        with self._lock.writer():
            with suppress(KeyError):
                del self._cache[key]
                del self._expire_info[key]
            return False

    def _has_expired(self, key):
        exp = self._expire_info.get(key, -1)
        if exp is None or exp > time.time():
            return False
        return True

    def _cull(self):
        if self._cull_frequency == 0:
            self.clear()
        else:
            doomed = [k for (i, k) in enumerate(self._cache) if i % self._cull_frequency == 0]
            for k in doomed:
                self._delete(k)

    def _delete(self, key):
        with suppress(KeyError):
            del self._cache[key]

        with suppress(KeyError):
            del self._expire_info[key]

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        with self._lock.writer():
            self._delete(key)

    def clear(self):
        self._cache.clear()
        self._expire_info.clear()
