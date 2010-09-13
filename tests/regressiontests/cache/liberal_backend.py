from django.core.cache.backends.locmem import CacheClass as LocMemCacheClass

class LiberalKeyValidationMixin(object):
    def validate_key(self, key):
        pass

class CacheClass(LiberalKeyValidationMixin, LocMemCacheClass):
    pass

