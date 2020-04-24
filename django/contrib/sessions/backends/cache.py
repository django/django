from django.conf import settings
from django.contrib.sessions.backends.base import (
    CreateError, HashingSessionBase, UpdateError,
)
from django.core.cache import caches

KEY_PREFIX = "django.contrib.sessions.cache"


class SessionStore(HashingSessionBase):
    """
    A cache-based session store.
    """
    cache_key_prefix = KEY_PREFIX
    _cache = caches[settings.SESSION_CACHE_ALIAS]

    @classmethod
    def get_cache_key(cls, backend_key):
        return cls.cache_key_prefix + backend_key

    @property
    def cache_key(self):
        backend_key = self.get_backend_key(self._get_or_create_frontend_key())
        return self.cache_key_prefix + backend_key

    @classmethod
    def _load_data(cls, backend_key):
        """
        Load the session data for the session identified
        by 'backend_key' and return a dictionary.
        Return None if the session doesn't exists.
        """
        try:
            session_data = cls._cache.get(cls.get_cache_key(backend_key))
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            session_data = None
        return session_data

    def create(self):
        """
        Create a new session instance. Will attempt 10000 times
        to generate a unique key and save the result once
        result once (with empty data) before the method returns.
        Raise RuntimeError after 10000 failed attempts.
        """
        # Because a cache can fail silently (e.g. memcache), we don't know if
        # we are failing to create a new session because of a key collision or
        # because the cache is missing. So we try for a (large) number of times
        # and then raise an exception. That's the risk you shoulder if using
        # cache backing.
        try:
            super().create(max_attempts=10000)
        except CreateError:
            raise RuntimeError(
                "Unable to create a new session key. "
                "It is likely that the cache is unavailable.")

    @classmethod
    def _save(cls, backend_key, session_data, must_create=False):
        cache_key = cls.get_cache_key(backend_key)

        if must_create:
            func = cls._cache.add
        elif cls._cache.get(cache_key) is not None:
            func = cls._cache.set
        else:
            raise UpdateError

        result = func(cache_key,
                      session_data,
                      cls._get_expiry_age(session_data))

        if must_create and not result:
            raise CreateError

    @classmethod
    def _exists(cls, backend_key):
        return cls.get_cache_key(backend_key) in cls._cache

    @classmethod
    def _delete(cls, backend_key):
        cls._cache.delete(cls.get_cache_key(backend_key))

    @classmethod
    def clear_expired(cls):
        pass
