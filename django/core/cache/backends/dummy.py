"Dummy cache backend"

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache


class DummyCache(BaseCache):
    def __init__(self, host, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return True

    async def add_async(self, *args, **kwargs):
        return self.add(*args, **kwargs)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return default

    async def get_async(self, *args, **kwargs):
        return self.get(*args, **kwargs)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)

    async def set_async(self, *args, **kwargs):
        return self.set(*args, **kwargs)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        self.validate_key(key)
        return False

    async def touch_async(self, *args, **kwargs):
        return self.touch(*args, **kwargs)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return False

    async def delete_async(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return False

    async def has_key_async(self, *args, **kwargs):
        return self.has_key(*args, **kwargs)

    def clear(self):
        pass

    async def clear_async(self):
        pass
