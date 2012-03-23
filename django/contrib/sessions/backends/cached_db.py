"""
Cached, database-backed sessions.
"""

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.core.cache import cache

KEY_PREFIX = "django.contrib.sessions.cached_db"


class SessionStore(DBStore):
    """
    Implements cached, database backed sessions.
    """

    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)

    @property
    def cache_key(self):
        return KEY_PREFIX + self._get_or_create_session_key()

    def load(self):
        try:
            data = cache.get(self.cache_key, None)
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            data = None
        if data is None:
            data = super(SessionStore, self).load()
            cache.set(self.cache_key, data, settings.SESSION_COOKIE_AGE)
        return data

    def exists(self, session_key):
        if (KEY_PREFIX + session_key) in cache:
            return True
        return super(SessionStore, self).exists(session_key)

    def save(self, must_create=False):
        super(SessionStore, self).save(must_create)
        cache.set(self.cache_key, self._session, settings.SESSION_COOKIE_AGE)

    def delete(self, session_key=None):
        super(SessionStore, self).delete(session_key)
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        cache.delete(KEY_PREFIX + session_key)

    def flush(self):
        """
        Removes the current session data from the database and regenerates the
        key.
        """
        self.clear()
        self.delete(self.session_key)
        self.create()
