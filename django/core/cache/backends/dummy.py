"Dummy cache backend"

from django.core.cache.backends.base import BaseCache

class CacheClass(BaseCache):
    def __init__(self, *args, **kwargs):
        pass

    def add(self, *args, **kwargs):
        return True

    def get(self, key, default=None):
        return default

    def set(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def get_many(self, *args, **kwargs):
        return {}

    def has_key(self, *args, **kwargs):
        return False
