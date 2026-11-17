from django.conf import settings
from django.contrib.sessions.backends.base import CreateError, SessionBase, UpdateError
from django.core.cache import caches

KEY_PREFIX = "django.contrib.sessions.cache"


class SessionStore(SessionBase):
    """
    A cache-based session store.
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

    def _load_kept_under_session_key(self):
        """
        While SESSION_STORE_KEY_HASH is "transition", return the data of the
        session if it's still kept under its session key.
        """
        cache_keys = self._get_cache_keys(self.session_key)
        if len(cache_keys) == 1:
            return None
        session_data = self._cache.get(cache_keys[1])
        if session_data is None:
            # A concurrent request may have just saved the session, which
            # moves it to its hashed backend key.
            return self._cache.get(cache_keys[0])
        # Have the session saved.
        self.modified = True
        return session_data

    async def _aload_kept_under_session_key(self):
        """See _load_kept_under_session_key()."""
        cache_keys = self._get_cache_keys(self.session_key)
        if len(cache_keys) == 1:
            return None
        session_data = await self._cache.aget(cache_keys[1])
        if session_data is None:
            return await self._cache.aget(cache_keys[0])
        self.modified = True
        return session_data

    def load(self):
        try:
            session_data = self._cache.get(self.cache_key)
            if session_data is None:
                session_data = self._load_kept_under_session_key()
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            session_data = None
        if session_data is not None:
            return session_data
        self._session_key = None
        return {}

    async def aload(self):
        try:
            session_data = await self._cache.aget(await self.acache_key())
            if session_data is None:
                session_data = await self._aload_kept_under_session_key()
        except Exception:
            session_data = None
        if session_data is not None:
            return session_data
        self._session_key = None
        return {}

    def create(self):
        # Because a cache can fail silently (e.g. memcache), we don't know if
        # we are failing to create a new session because of a key collision or
        # because the cache is missing. So we try for a (large) number of times
        # and then raise an exception. That's the risk you shoulder if using
        # cache backing.
        for i in range(10000):
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return
        raise RuntimeError(
            "Unable to create a new session key. "
            "It is likely that the cache is unavailable."
        )

    async def acreate(self):
        for i in range(10000):
            self._session_key = await self._aget_new_session_key()
            try:
                await self.asave(must_create=True)
            except CreateError:
                continue
            self.modified = True
            return
        raise RuntimeError(
            "Unable to create a new session key. "
            "It is likely that the cache is unavailable."
        )

    def save(self, must_create=False):
        if self.session_key is None:
            return self.create()
        if must_create:
            func = self._cache.add
        elif any(
            self._cache.get(key) is not None
            for key in self._get_cache_keys(self.session_key)
        ):
            func = self._cache.set
        else:
            raise UpdateError
        session_data = self._get_session(no_load=must_create)
        expiry_age = self.get_expiry_age()
        result = func(self.cache_key, session_data, expiry_age)
        if must_create:
            if not result:
                raise CreateError
            return
        # While SESSION_STORE_KEY_HASH is "transition", the session may have
        # been kept under its session key. A cache can fail silently, so that
        # copy is deleted only once the session is under its hashed backend
        # key, or has expired.
        cache_keys = self._get_cache_keys(self.session_key)
        if len(cache_keys) > 1 and (
            expiry_age <= 0 or self._cache.get(cache_keys[0]) is not None
        ):
            self._cache.delete(cache_keys[1])

    async def asave(self, must_create=False):
        if self.session_key is None:
            return await self.acreate()
        if must_create:
            func = self._cache.aadd
        elif [
            key
            for key in self._get_cache_keys(self.session_key)
            if await self._cache.aget(key) is not None
        ]:
            func = self._cache.aset
        else:
            raise UpdateError
        session_data = await self._aget_session(no_load=must_create)
        expiry_age = await self.aget_expiry_age()
        result = await func(await self.acache_key(), session_data, expiry_age)
        if must_create:
            if not result:
                raise CreateError
            return
        cache_keys = self._get_cache_keys(self.session_key)
        if len(cache_keys) > 1 and (
            expiry_age <= 0 or await self._cache.aget(cache_keys[0]) is not None
        ):
            await self._cache.adelete(cache_keys[1])

    def exists(self, session_key):
        return bool(session_key) and any(
            key in self._cache for key in self._get_cache_keys(session_key)
        )

    async def aexists(self, session_key):
        if not session_key:
            return False
        for key in self._get_cache_keys(session_key):
            if await self._cache.ahas_key(key):
                return True
        return False

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        # The session key comes first, so that the session is found even if a
        # concurrent request is moving it to its hashed backend key.
        for key in reversed(self._get_cache_keys(session_key)):
            self._cache.delete(key)

    async def adelete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        for key in reversed(self._get_cache_keys(session_key)):
            await self._cache.adelete(key)

    @classmethod
    def clear_expired(cls):
        pass

    @classmethod
    async def aclear_expired(cls):
        pass
