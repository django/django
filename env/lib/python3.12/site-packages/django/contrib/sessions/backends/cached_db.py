"""
Cached, database-backed sessions.
"""

import logging

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.core.cache import caches

KEY_PREFIX = "django.contrib.sessions.cached_db"

logger = logging.getLogger("django.contrib.sessions")


class SessionStore(DBStore):
    """
    Implement cached, database backed sessions.
    """

    cache_key_prefix = KEY_PREFIX

    def __init__(self, session_key=None):
        self._cache = caches[settings.SESSION_CACHE_ALIAS]
        super().__init__(session_key)

    @property
    def cache_key(self):
        return self.cache_key_prefix + self._get_or_create_session_key()

    async def acache_key(self):
        return self.cache_key_prefix + await self._aget_or_create_session_key()

    def load(self):
        try:
            data = self._cache.get(self.cache_key)
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            data = None

        if data is None:
            s = self._get_session_from_db()
            if s:
                data = self.decode(s.session_data)
                self._cache.set(
                    self.cache_key, data, self.get_expiry_age(expiry=s.expire_date)
                )
            else:
                data = {}
        return data

    async def aload(self):
        try:
            data = await self._cache.aget(await self.acache_key())
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            data = None

        if data is None:
            s = await self._aget_session_from_db()
            if s:
                data = self.decode(s.session_data)
                await self._cache.aset(
                    await self.acache_key(),
                    data,
                    await self.aget_expiry_age(expiry=s.expire_date),
                )
            else:
                data = {}
        return data

    def exists(self, session_key):
        return (
            session_key
            and (self.cache_key_prefix + session_key) in self._cache
            or super().exists(session_key)
        )

    async def aexists(self, session_key):
        return (
            session_key
            and (self.cache_key_prefix + session_key) in self._cache
            or await super().aexists(session_key)
        )

    def save(self, must_create=False):
        super().save(must_create)
        try:
            self._cache.set(self.cache_key, self._session, self.get_expiry_age())
        except Exception:
            logger.exception("Error saving to cache (%s)", self._cache)

    async def asave(self, must_create=False):
        await super().asave(must_create)
        try:
            await self._cache.aset(
                await self.acache_key(),
                self._session,
                await self.aget_expiry_age(),
            )
        except Exception:
            logger.exception("Error saving to cache (%s)", self._cache)

    def delete(self, session_key=None):
        super().delete(session_key)
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        self._cache.delete(self.cache_key_prefix + session_key)

    async def adelete(self, session_key=None):
        await super().adelete(session_key)
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        await self._cache.adelete(self.cache_key_prefix + session_key)

    def flush(self):
        """
        Remove the current session data from the database and regenerate the
        key.
        """
        self.clear()
        self.delete(self.session_key)
        self._session_key = None

    async def aflush(self):
        """See flush()."""
        self.clear()
        await self.adelete(self.session_key)
        self._session_key = None
