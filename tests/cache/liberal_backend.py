from django.core.cache.backends.locmem import LocMemCache


class LiberalKeyValidationMixin(object):
    def validate_key(self, key):
        pass

class CacheClass(LiberalKeyValidationMixin, LocMemCache):
    pass

