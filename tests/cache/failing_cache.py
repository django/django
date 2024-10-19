from django.core.cache.backends.locmem import LocMemCache


class CacheClass(LocMemCache):

    def set(self, *args, **kwargs):
        raise Exception("Faked exception saving to cache")

    async def aset(self, *args, **kwargs):
        raise Exception("Faked exception saving to cache")
