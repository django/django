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

    def load(self):
        data = cache.get(KEY_PREFIX + self.session_key, None)
        if data is None:
            data = super(SessionStore, self).load()
            cache.set(KEY_PREFIX + self.session_key, data, 
                      settings.SESSION_COOKIE_AGE)
        return data

    def exists(self, session_key):
        return super(SessionStore, self).exists(session_key)

    def save(self, must_create=False):
        super(SessionStore, self).save(must_create)
        cache.set(KEY_PREFIX + self.session_key, self._session, 
                  settings.SESSION_COOKIE_AGE)

    def delete(self, session_key=None):
        super(SessionStore, self).delete(session_key)
        cache.delete(KEY_PREFIX + (session_key or self.session_key))

    def flush(self):
        """
        Removes the current session data from the database and regenerates the
        key.
        """
        self.clear()
        self.delete(self.session_key)
        self.create()
