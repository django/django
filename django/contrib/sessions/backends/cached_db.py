"""
Cached, database-backed sessions.
"""

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.core.cache import caches

KEY_PREFIX = "django.contrib.sessions.cached_db"

def get_cache_store():
    return caches[settings.SESSION_CACHE_ALIAS]

class SessionStore(DBStore):
    """
    Implement cached, database backed sessions.
    """
    cache_key_prefix = KEY_PREFIX
    _cache = get_cache_store()

    @classmethod
    def _get_cache_key(cls, backend_key):
        return cls.cache_key_prefix + str(backend_key)

    @property
    def cache_key(self):
        return self._get_cache_key(
            self.get_backend_key(
                self._get_or_create_session_key()))

    @classmethod
    def _get_cache(cls, cache_key):
        data = None
        try:
            data = cls._cache.get(cache_key)
        except:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            data = None
        return data

    @classmethod
    def _set_cache(cls, cache_key, session_data):
        cls._cache.set(cache_key, session_data, cls._get_expiry_age(session_data))

    # DBStore methods

    @classmethod
    def _load_data(cls, backend_key):
        """
        Return cashed data if present, otherwise call DBStore.load()
        and cache the result if any data is returned.
        Return None when requested session doesn't exist.
        """
        cache_key = cls._get_cache_key(backend_key)

        data = cls._get_cache(cache_key)

        if not data is None:
            return data

        s = super()._load_data(backend_key)

        if not s:
            return None

        data = cls._decode(s.session_data)
        cls._set_cache(cache_key, data)

        return data

    @classmethod
    def _exists(cls, backend_key):
        if cls._get_cache_key(backend_key) in cls._cache:
            return True

        return super()._exists(backend_key)
  
    @classmethod
    def _save(cls, backend_key, session_data, must_create=False):
        super()._save(backend_key, session_data, must_create)
        cls._set_cache(cls._get_cache_key(backend_key), session_data)

    @classmethod
    def _delete(cls, backend_key):
        super()._delete(backend_key)
        cache_key = cls._get_cache_key(backend_key)
        cls._cache.delete(cache_key)
