from django.core.cache.backends.locmem import LocMemCache


class LiberalKeyValidationMixin(object):
    def validate_key(self, key):
        pass

class CacheClass(LiberalKeyValidationMixin, LocMemCache):
    pass

class CountingCache(LocMemCache):
    """A Cache class that tracks how many times it has been instantiated."""
    count = 0
    def __init__(self, *args, **kwargs):
        super(CountingCache, self).__init__(*args, **kwargs)
        CountingCache.count += 1
