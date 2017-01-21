"""
Cached, database-backed sessions.
"""

import logging

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.core.cache import caches
from django.core.exceptions import SuspiciousOperation
from django.utils import timezone
from django.utils.encoding import force_text

KEY_PREFIX = "django.contrib.sessions.cached_db"


class SessionStore(DBStore):
    """
    Implements cached, database backed sessions.
    """
    cache_key_prefix = KEY_PREFIX

    def __init__(self, session_key=None):
        self._cache = caches[settings.SESSION_CACHE_ALIAS]
        super().__init__(session_key)

    @property
    def cache_key(self):
        return self.cache_key_prefix + self._get_or_create_session_key()

    def load(self):
        try:
            data = self._cache.get(self.cache_key)
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            data = None

        if data is None:
            # Duplicate DBStore.load, because we need to keep track
            # of the expiry date to set it properly in the cache.
            try:
                s = self.model.objects.get(
                    session_key=self.session_key,
                    expire_date__gt=timezone.now()
                )
                data = self.decode(s.session_data)
                self._cache.set(self.cache_key, data, self.get_expiry_age(expiry=s.expire_date))
            except (self.model.DoesNotExist, SuspiciousOperation) as e:
                if isinstance(e, SuspiciousOperation):
                    logger = logging.getLogger('django.security.%s' % e.__class__.__name__)
                    logger.warning(force_text(e))
                self._session_key = None
                data = {}
        return data

    def exists(self, session_key):
        if session_key and (self.cache_key_prefix + session_key) in self._cache:
            return True
        return super().exists(session_key)

    def save(self, must_create=False):
        super().save(must_create)
        self._cache.set(self.cache_key, self._session, self.get_expiry_age())

    def delete(self, session_key=None):
        super().delete(session_key)
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        self._cache.delete(self.cache_key_prefix + session_key)

    def flush(self):
        """
        Removes the current session data from the database and regenerates the
        key.
        """
        self.clear()
        self.delete(self.session_key)
        self._session_key = None
