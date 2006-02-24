"Single-process in-memory cache backend."

from django.core.cache.backends.base import BaseCache
import time

class CacheClass(BaseCache):
    def __init__(self, host, params):
        BaseCache.__init__(self, params)
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
