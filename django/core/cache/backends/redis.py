"Redis cache backend"

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache


class BaseRedisCache(BaseCache):
    def __init__(self, server, params, library):
        super().__init__(params)
        self._lib = library
        if server[0:8] != "redis://":
            self._servers = "redis://" + server
            return
        self._servers = server
        return


class RedisCache(BaseRedisCache):
    def __init__(self, server, params):
        import redis
        super().__init__(server, params, library=redis)

    @property
    def _cache(self):
        if getattr(self, '_client', None) is None:
            self._client = self._lib.StrictRedis.from_url(self._servers)
        return self._client

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        val = self._cache.get(key)
        if val is None:
            return default
        return val

    def get_many(self, keys, version=None):
        return self._cache.mget([self.make_key(key, version=version) for key in keys])

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        return self._cache.exists(key) == 1

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self._cache.set(key, value)
        return

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self._cache.setnx(key, value)
        return

    def incr(self, key, delta=1, version=None):
        if not self.has_key(key, version=version):
            raise ValueError("Key '%s' not found" % key)
        key = self.make_key(key, version=version)
        return self._cache.incr(key, amount=delta)

    def decr(self, key, delta=1, version=None):
        if not self.has_key(key, version=version):
            raise ValueError("Key '%s' not found" % key)
        key = self.make_key(key, version=version)
        return self._cache.decr(key, amount=delta)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        return self._cache.expire(key, timeout)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self._cache.delete(key)
        return

    def delete_many(self, keys, version=None):
        with self._cache.pipeline(transaction=False) as pipe:
            for key in keys:
                key = self.make_key(key, version=version)
                pipe.delete(key, 1)
            pipe.execute()

    def clear(self, all=False):
        """
        If need to delete all DBs, set all to True
        """
        if all:
            return self._cache.flushdb()
        return self._cache.flushall()
