import asyncio

from django.core.cache import CacheKeyWarning, cache
from django.test import SimpleTestCase, override_settings

from .tests import KEY_ERRORS_WITH_MEMCACHED_MSG


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
)
class AsyncDummyCacheTests(SimpleTestCase):
    async def test_simple(self):
        """Dummy cache backend ignores cache set calls."""
        await cache.aset("key", "value")
        self.assertIsNone(await cache.aget("key"))

    async def test_aadd(self):
        """Add doesn't do anything in dummy cache backend."""
        self.assertIs(await cache.aadd("key", "value"), True)
        self.assertIs(await cache.aadd("key", "new_value"), True)
        self.assertIsNone(await cache.aget("key"))

    async def test_non_existent(self):
        """Nonexistent keys aren't found in the dummy cache backend."""
        self.assertIsNone(await cache.aget("does_not_exist"))
        self.assertEqual(await cache.aget("does_not_exist", "default"), "default")

    async def test_aget_many(self):
        """aget_many() returns nothing for the dummy cache backend."""
        await cache.aset_many({"a": "a", "b": "b", "c": "c", "d": "d"})
        self.assertEqual(await cache.aget_many(["a", "c", "d"]), {})
        self.assertEqual(await cache.aget_many(["a", "b", "e"]), {})

    async def test_aget_many_invalid_key(self):
        msg = KEY_ERRORS_WITH_MEMCACHED_MSG % ":1:key with spaces"
        with self.assertWarnsMessage(CacheKeyWarning, msg):
            await cache.aget_many(["key with spaces"])

    async def test_adelete(self):
        """
        Cache deletion is transparently ignored on the dummy cache backend.
        """
        await cache.aset_many({"key1": "spam", "key2": "eggs"})
        self.assertIsNone(await cache.aget("key1"))
        self.assertIs(await cache.adelete("key1"), False)
        self.assertIsNone(await cache.aget("key1"))
        self.assertIsNone(await cache.aget("key2"))

    async def test_ahas_key(self):
        """ahas_key() doesn't ever return True for the dummy cache backend."""
        await cache.aset("hello1", "goodbye1")
        self.assertIs(await cache.ahas_key("hello1"), False)
        self.assertIs(await cache.ahas_key("goodbye1"), False)

    async def test_aincr(self):
        """Dummy cache values can't be incremented."""
        await cache.aset("answer", 42)
        with self.assertRaises(ValueError):
            await cache.aincr("answer")
        with self.assertRaises(ValueError):
            await cache.aincr("does_not_exist")
        with self.assertRaises(ValueError):
            await cache.aincr("does_not_exist", -1)

    async def test_adecr(self):
        """Dummy cache values can't be decremented."""
        await cache.aset("answer", 42)
        with self.assertRaises(ValueError):
            await cache.adecr("answer")
        with self.assertRaises(ValueError):
            await cache.adecr("does_not_exist")
        with self.assertRaises(ValueError):
            await cache.adecr("does_not_exist", -1)

    async def test_atouch(self):
        self.assertIs(await cache.atouch("key"), False)

    async def test_data_types(self):
        """All data types are ignored equally by the dummy cache."""

        def f():
            return 42

        class C:
            def m(n):
                return 24

        data = {
            "string": "this is a string",
            "int": 42,
            "list": [1, 2, 3, 4],
            "tuple": (1, 2, 3, 4),
            "dict": {"A": 1, "B": 2},
            "function": f,
            "class": C,
        }
        await cache.aset("data", data)
        self.assertIsNone(await cache.aget("data"))

    async def test_expiration(self):
        """Expiration has no effect on the dummy cache."""
        await cache.aset("expire1", "very quickly", 1)
        await cache.aset("expire2", "very quickly", 1)
        await cache.aset("expire3", "very quickly", 1)

        await asyncio.sleep(2)
        self.assertIsNone(await cache.aget("expire1"))

        self.assertIs(await cache.aadd("expire2", "new_value"), True)
        self.assertIsNone(await cache.aget("expire2"))
        self.assertIs(await cache.ahas_key("expire3"), False)

    async def test_unicode(self):
        """Unicode values are ignored by the dummy cache."""
        tests = {
            "ascii": "ascii_value",
            "unicode_ascii": "Iñtërnâtiônàlizætiøn1",
            "Iñtërnâtiônàlizætiøn": "Iñtërnâtiônàlizætiøn2",
            "ascii2": {"x": 1},
        }
        for key, value in tests.items():
            with self.subTest(key=key):
                await cache.aset(key, value)
                self.assertIsNone(await cache.aget(key))

    async def test_aset_many(self):
        """aset_many() does nothing for the dummy cache backend."""
        self.assertEqual(await cache.aset_many({"a": 1, "b": 2}), [])
        self.assertEqual(
            await cache.aset_many({"a": 1, "b": 2}, timeout=2, version="1"),
            [],
        )

    async def test_aset_many_invalid_key(self):
        msg = KEY_ERRORS_WITH_MEMCACHED_MSG % ":1:key with spaces"
        with self.assertWarnsMessage(CacheKeyWarning, msg):
            await cache.aset_many({"key with spaces": "foo"})

    async def test_adelete_many(self):
        """adelete_many() does nothing for the dummy cache backend."""
        await cache.adelete_many(["a", "b"])

    async def test_adelete_many_invalid_key(self):
        msg = KEY_ERRORS_WITH_MEMCACHED_MSG % ":1:key with spaces"
        with self.assertWarnsMessage(CacheKeyWarning, msg):
            await cache.adelete_many({"key with spaces": "foo"})

    async def test_aclear(self):
        """aclear() does nothing for the dummy cache backend."""
        await cache.aclear()

    async def test_aclose(self):
        """aclose() does nothing for the dummy cache backend."""
        await cache.aclose()

    async def test_aincr_version(self):
        """Dummy cache versions can't be incremented."""
        await cache.aset("answer", 42)
        with self.assertRaises(ValueError):
            await cache.aincr_version("answer")
        with self.assertRaises(ValueError):
            await cache.aincr_version("answer", version=2)
        with self.assertRaises(ValueError):
            await cache.aincr_version("does_not_exist")

    async def test_adecr_version(self):
        """Dummy cache versions can't be decremented."""
        await cache.aset("answer", 42)
        with self.assertRaises(ValueError):
            await cache.adecr_version("answer")
        with self.assertRaises(ValueError):
            await cache.adecr_version("answer", version=2)
        with self.assertRaises(ValueError):
            await cache.adecr_version("does_not_exist")

    async def test_aget_or_set(self):
        self.assertEqual(await cache.aget_or_set("key", "default"), "default")
        self.assertIsNone(await cache.aget_or_set("key", None))

    async def test_aget_or_set_callable(self):
        def my_callable():
            return "default"

        self.assertEqual(await cache.aget_or_set("key", my_callable), "default")
        self.assertEqual(await cache.aget_or_set("key", my_callable()), "default")
