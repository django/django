"""Redis cache backend."""

import asyncio
import pickle
import random
import re
import threading

import django
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils.functional import cached_property
from django.utils.module_loading import import_string


class RedisSerializer:
    def __init__(self, protocol=None):
        self.protocol = pickle.HIGHEST_PROTOCOL if protocol is None else protocol

    def dumps(self, obj):
        # For better incr() and decr() atomicity, don't pickle integers.
        # Using type() rather than isinstance() matches only integers and not
        # subclasses like bool.
        if type(obj) is int:
            return obj
        return pickle.dumps(obj, self.protocol)

    def loads(self, data):
        try:
            return int(data)
        except ValueError:
            return pickle.loads(data)


class RedisCacheClient:
    def __init__(
        self,
        servers,
        serializer=None,
        pool_class=None,
        parser_class=None,
        **options,
    ):
        import redis

        self._lib = redis
        self._servers = servers
        self._pools = {}
        # For async operations, store pools per event loop
        self._async_pools = {}
        self._async_pools_lock = threading.Lock()

        self._client = self._lib.Redis

        if isinstance(pool_class, str):
            pool_class = import_string(pool_class)
        self._pool_class = pool_class or self._lib.ConnectionPool

        if isinstance(serializer, str):
            serializer = import_string(serializer)
        if callable(serializer):
            serializer = serializer()
        self._serializer = serializer or RedisSerializer()

        if isinstance(parser_class, str):
            parser_class = import_string(parser_class)
        parser_class = parser_class or self._lib.connection.DefaultParser

        version = django.get_version()
        if hasattr(self._lib, "DriverInfo"):
            driver_info = self._lib.DriverInfo().add_upstream_driver("django", version)
            driver_info_options = {"driver_info": driver_info}
        else:
            # DriverInfo is not available in this redis-py version.
            driver_info_options = {"lib_name": f"redis-py(django_v{version})"}

        self._pool_options = {
            "parser_class": parser_class,
            **driver_info_options,
            **options,
        }

    def _get_connection_pool_index(self, write):
        # Write to the first server. Read from other servers if there are more,
        # otherwise read from the first server.
        if write or len(self._servers) == 1:
            return 0
        return random.randint(1, len(self._servers) - 1)

    def _get_connection_pool(self, write):
        index = self._get_connection_pool_index(write)
        if index not in self._pools:
            self._pools[index] = self._pool_class.from_url(
                self._servers[index],
                **self._pool_options,
            )
        return self._pools[index]

    def _get_async_connection_pool(self, write):
        """Get an async connection pool for the current event loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop, fall back to sync
            return None

        loop_id = id(loop)
        index = self._get_connection_pool_index(write)
        pool_key = (loop_id, index)

        with self._async_pools_lock:
            if pool_key not in self._async_pools:
                # Create async connection pool for this event loop
                async_pool_class = self._lib.asyncio.ConnectionPool
                self._async_pools[pool_key] = async_pool_class.from_url(
                    self._servers[index],
                    **self._pool_options,
                )
            return self._async_pools[pool_key]

    def get_client(self, key=None, *, write=False):
        # key is used so that the method signature remains the same and custom
        # cache client can be implemented which might require the key to select
        # the server, e.g. sharding.
        pool = self._get_connection_pool(write)
        return self._client(connection_pool=pool)

    async def get_async_client(self, key=None, *, write=False):
        """Get an async Redis client for the current event loop."""
        pool = self._get_async_connection_pool(write)
        if pool is None:
            raise RuntimeError(
                "Cannot use async Redis client without an active event loop. "
                "Async operations require an async context."
            )
        return self._lib.asyncio.Redis(connection_pool=pool)

    def add(self, key, value, timeout):
        client = self.get_client(key, write=True)
        value = self._serializer.dumps(value)

        if timeout == 0:
            if ret := bool(client.set(key, value, nx=True)):
                client.delete(key)
            return ret
        else:
            return bool(client.set(key, value, ex=timeout, nx=True))

    def get(self, key, default):
        client = self.get_client(key)
        value = client.get(key)
        return default if value is None else self._serializer.loads(value)

    def set(self, key, value, timeout):
        client = self.get_client(key, write=True)
        value = self._serializer.dumps(value)
        if timeout == 0:
            client.delete(key)
        else:
            client.set(key, value, ex=timeout)

    def touch(self, key, timeout):
        client = self.get_client(key, write=True)
        if timeout is None:
            return bool(client.persist(key))
        else:
            return bool(client.expire(key, timeout))

    def delete(self, key):
        client = self.get_client(key, write=True)
        return bool(client.delete(key))

    def get_many(self, keys):
        client = self.get_client(None)
        ret = client.mget(keys)
        return {
            k: self._serializer.loads(v) for k, v in zip(keys, ret) if v is not None
        }

    def has_key(self, key):
        client = self.get_client(key)
        return bool(client.exists(key))

    def incr(self, key, delta):
        client = self.get_client(key, write=True)
        if not client.exists(key):
            raise ValueError("Key '%s' not found." % key)
        return client.incr(key, delta)

    def set_many(self, data, timeout):
        client = self.get_client(None, write=True)
        pipeline = client.pipeline()
        pipeline.mset({k: self._serializer.dumps(v) for k, v in data.items()})

        if timeout is not None:
            # Setting timeout for each key as redis does not support timeout
            # with mset().
            for key in data:
                pipeline.expire(key, timeout)
        pipeline.execute()

    def delete_many(self, keys):
        client = self.get_client(None, write=True)
        client.delete(*keys)

    def clear(self):
        client = self.get_client(None, write=True)
        return bool(client.flushdb())

    # Async methods using redis-py's async client
    async def aadd(self, key, value, timeout):
        client = await self.get_async_client(key, write=True)
        value = self._serializer.dumps(value)

        if timeout == 0:
            if ret := bool(await client.set(key, value, nx=True)):
                await client.delete(key)
            return ret
        else:
            return bool(await client.set(key, value, ex=timeout, nx=True))

    async def aget(self, key, default):
        client = await self.get_async_client(key)
        value = await client.get(key)
        return default if value is None else self._serializer.loads(value)

    async def aset(self, key, value, timeout):
        client = await self.get_async_client(key, write=True)
        value = self._serializer.dumps(value)
        if timeout == 0:
            await client.delete(key)
        else:
            await client.set(key, value, ex=timeout)

    async def atouch(self, key, timeout):
        client = await self.get_async_client(key, write=True)
        if timeout is None:
            return bool(await client.persist(key))
        else:
            return bool(await client.expire(key, timeout))

    async def adelete(self, key):
        client = await self.get_async_client(key, write=True)
        return bool(await client.delete(key))

    async def aget_many(self, keys):
        client = await self.get_async_client(None)
        ret = await client.mget(keys)
        return {
            k: self._serializer.loads(v) for k, v in zip(keys, ret) if v is not None
        }

    async def ahas_key(self, key):
        client = await self.get_async_client(key)
        return bool(await client.exists(key))

    async def aincr(self, key, delta):
        client = await self.get_async_client(key, write=True)
        if not await client.exists(key):
            raise ValueError("Key '%s' not found." % key)
        return await client.incr(key, delta)

    async def aset_many(self, data, timeout):
        client = await self.get_async_client(None, write=True)
        pipeline = client.pipeline()
        pipeline.mset({k: self._serializer.dumps(v) for k, v in data.items()})

        if timeout is not None:
            # Setting timeout for each key as redis does not support timeout
            # with mset().
            for key in data:
                pipeline.expire(key, timeout)
        await pipeline.execute()

    async def adelete_many(self, keys):
        client = await self.get_async_client(None, write=True)
        await client.delete(*keys)

    async def aclear(self):
        client = await self.get_async_client(None, write=True)
        return bool(await client.flushdb())


class RedisCache(BaseCache):
    def __init__(self, server, params):
        super().__init__(params)
        if isinstance(server, str):
            self._servers = re.split("[;,]", server)
        else:
            self._servers = server

        self._class = RedisCacheClient
        self._options = params.get("OPTIONS", {})

    @cached_property
    def _cache(self):
        return self._class(self._servers, **self._options)

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):
        if timeout == DEFAULT_TIMEOUT:
            timeout = self.default_timeout
        # The key will be made persistent if None used as a timeout.
        # Non-positive values will cause the key to be deleted.
        return None if timeout is None else max(0, int(timeout))

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.add(key, value, self.get_backend_timeout(timeout))

    def get(self, key, default=None, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.get(key, default)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        self._cache.set(key, value, self.get_backend_timeout(timeout))

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.touch(key, self.get_backend_timeout(timeout))

    def delete(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.delete(key)

    def get_many(self, keys, version=None):
        key_map = {
            self.make_and_validate_key(key, version=version): key for key in keys
        }
        ret = self._cache.get_many(key_map.keys())
        return {key_map[k]: v for k, v in ret.items()}

    def has_key(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.has_key(key)

    def incr(self, key, delta=1, version=None):
        key = self.make_and_validate_key(key, version=version)
        return self._cache.incr(key, delta)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        if not data:
            return []
        safe_data = {}
        for key, value in data.items():
            key = self.make_and_validate_key(key, version=version)
            safe_data[key] = value
        self._cache.set_many(safe_data, self.get_backend_timeout(timeout))
        return []

    def delete_many(self, keys, version=None):
        if not keys:
            return
        safe_keys = [self.make_and_validate_key(key, version=version) for key in keys]
        self._cache.delete_many(safe_keys)

    def clear(self):
        return self._cache.clear()

    # Async methods using redis-py's async client
    async def aadd(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return await self._cache.aadd(key, value, self.get_backend_timeout(timeout))

    async def aget(self, key, default=None, version=None):
        key = self.make_and_validate_key(key, version=version)
        return await self._cache.aget(key, default)

    async def aset(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        await self._cache.aset(key, value, self.get_backend_timeout(timeout))

    async def atouch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_and_validate_key(key, version=version)
        return await self._cache.atouch(key, self.get_backend_timeout(timeout))

    async def adelete(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return await self._cache.adelete(key)

    async def aget_many(self, keys, version=None):
        key_map = {
            self.make_and_validate_key(key, version=version): key for key in keys
        }
        ret = await self._cache.aget_many(key_map.keys())
        return {key_map[k]: v for k, v in ret.items()}

    async def ahas_key(self, key, version=None):
        key = self.make_and_validate_key(key, version=version)
        return await self._cache.ahas_key(key)

    async def aincr(self, key, delta=1, version=None):
        key = self.make_and_validate_key(key, version=version)
        return await self._cache.aincr(key, delta)

    async def aset_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        if not data:
            return []
        safe_data = {}
        for key, value in data.items():
            key = self.make_and_validate_key(key, version=version)
            safe_data[key] = value
        await self._cache.aset_many(safe_data, self.get_backend_timeout(timeout))
        return []

    async def adelete_many(self, keys, version=None):
        if not keys:
            return
        safe_keys = [self.make_and_validate_key(key, version=version) for key in keys]
        await self._cache.adelete_many(safe_keys)

    async def aclear(self):
        return await self._cache.aclear()
