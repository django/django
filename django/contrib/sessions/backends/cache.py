from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.core.cache import cache

class SessionStore(SessionBase):
    """
    A cache-based session store. 
    """
    def __init__(self, session_key=None):
        self._cache = cache
        super(SessionStore, self).__init__(session_key)
        
    def load(self):
        session_data = self._cache.get(self.session_key)
        return session_data or {}

    def save(self):
        self._cache.set(self.session_key, self._session, settings.SESSION_COOKIE_AGE)

    def exists(self, session_key):
        if self._cache.get(session_key):
            return True
        return False
        
    def delete(self, session_key):
        self._cache.delete(session_key)