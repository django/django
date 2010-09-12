"Dummy cache backend"

from django.core.cache.backends.base import BaseCache

class CacheClass(BaseCache):
    def __init__(self, *args, **kwargs):
        pass

    def add(self, key, *args, **kwargs):
        self.validate_key(key)
        return True

    def get(self, key, default=None):
        self.validate_key(key)
        return default

    def set(self, key, *args, **kwargs):
        self.validate_key(key)

    def delete(self, key, *args, **kwargs):
        self.validate_key(key)

    def get_many(self, *args, **kwargs):
        return {}

    def has_key(self, key, *args, **kwargs):
        self.validate_key(key)
        return False

    def set_many(self, *args, **kwargs):
        pass

    def delete_many(self, *args, **kwargs):
        pass

    def clear(self):
        pass
