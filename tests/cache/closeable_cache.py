from django.core.cache.backends.locmem import LocMemCache


class CloseHookMixin(object):
    closed = False

    def close(self, **kwargs):
        self.closed = True

class CacheClass(CloseHookMixin, LocMemCache):
    pass
