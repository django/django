"Dummy cache backend"

from django.core.cache.backends.base import BaseCache

class CacheClass(BaseCache):
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def get_many(self, *args, **kwargs):
        pass

    def has_key(self, *args, **kwargs):
        return False
