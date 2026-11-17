"""
Cached, database-backed sessions.
"""

import logging

from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.core.cache import caches
from django.db import connections, transaction

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
        return self.cache_key_prefix + self.get_backend_key(
            self._get_or_create_session_key()
        )

    async def acache_key(self):
        return self.cache_key_prefix + self.get_backend_key(
            await self._aget_or_create_session_key()
        )

    def _get_cache_keys(self, session_key):
        return [
            self.cache_key_prefix + backend_key
            for backend_key in self._get_backend_keys(session_key)
        ]

    def _is_cacheable(self, using, created=False):
        """
        While SESSION_STORE_KEY_HASH is "transition", return whether the
        session, which was just loaded from or saved to the `using` database,
        can be cached: it must be kept under its hashed backend key, and the
        database must not be in a transaction, which may be rolled back and
        return a session that it moved to its session key.

        A session that was just created is cached nonetheless, as with the
        other values of the setting, so it stays in the cache if the
        transaction that created it is rolled back.
        """
        if settings.SESSION_STORE_KEY_HASH != "transition":
            return True
        if self._kept_under_session_key:
            return False
        # A session that was just created isn't a session that was moved.
        if created:
            return True
        # Whichever session store moved the session in this transaction.
        connection = connections[using]
        return not connection.in_atomic_block and connection.get_autocommit()

    async def _ais_cacheable(self, using, created=False):
        if settings.SESSION_STORE_KEY_HASH != "transition":
            return True
        # The transaction is the one of the thread that accesses the database.
        return await sync_to_async(self._is_cacheable)(using, created)

    def _uncache_on_commit(self, using, cache_keys):
        """
        While SESSION_STORE_KEY_HASH is "transition", a session that's saved
        inside a transaction is removed from the cache. Have it removed again
        when the transaction is committed, because a concurrent request may
        cache it in the meantime, as the database has it until then.
        """
        # on_commit() isn't available when autocommit is turned off.
        if not connections[using].in_atomic_block:
            return
        cache = self._cache

        def uncache():
            try:
                cache.delete_many(cache_keys)
            except Exception:
                logger.exception("Error deleting from cache (%s)", cache)

        transaction.on_commit(uncache, using=using)

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
                if self._is_cacheable(s._state.db):
                    self._cache.set(
                        self.cache_key,
                        data,
                        self.get_expiry_age(expiry=s.expire_date),
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
                if await self._ais_cacheable(s._state.db):
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
            and any(key in self._cache for key in self._get_cache_keys(session_key))
            or super().exists(session_key)
        )

    async def aexists(self, session_key):
        return (
            session_key
            and any(key in self._cache for key in self._get_cache_keys(session_key))
            or await super().aexists(session_key)
        )

    def save(self, must_create=False):
        created = must_create or self.session_key is None
        super().save(must_create)
        try:
            if self._is_cacheable(self._saved_using, created):
                self._cache.set(self.cache_key, self._session, self.get_expiry_age())
                # The session isn't kept under its session key anymore.
                for key in self._get_cache_keys(self.session_key)[1:]:
                    self._cache.delete(key)
            else:
                cache_keys = self._get_cache_keys(self.session_key)
                self._cache.delete_many(cache_keys)
                self._uncache_on_commit(self._saved_using, cache_keys)
        except Exception:
            logger.exception("Error saving to cache (%s)", self._cache)

    async def asave(self, must_create=False):
        created = must_create or self.session_key is None
        await super().asave(must_create)
        try:
            if await self._ais_cacheable(self._saved_using, created):
                await self._cache.aset(
                    await self.acache_key(),
                    self._session,
                    await self.aget_expiry_age(),
                )
                for key in self._get_cache_keys(self.session_key)[1:]:
                    await self._cache.adelete(key)
            else:
                cache_keys = self._get_cache_keys(self.session_key)
                await self._cache.adelete_many(cache_keys)
                await sync_to_async(self._uncache_on_commit)(
                    self._saved_using, cache_keys
                )
        except Exception:
            logger.exception("Error saving to cache (%s)", self._cache)

    def delete(self, session_key=None):
        super().delete(session_key)
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        try:
            for key in reversed(self._get_cache_keys(session_key)):
                self._cache.delete(key)
        except Exception:
            logger.exception("Error deleting from cache (%s)", self._cache)

    async def adelete(self, session_key=None):
        await super().adelete(session_key)
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        try:
            for key in reversed(self._get_cache_keys(session_key)):
                await self._cache.adelete(key)
        except Exception:
            logger.exception("Error deleting from cache (%s)", self._cache)

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
