# -*- coding: utf-8 -*-

# Unit tests for cache framework
# Uses whatever cache backend is set in the test settings file.

from django.core.cache import cache
import time, unittest

# functions/classes for complex data type tests
def f():
    return 42
class C:
    def m(n):
        return 24

class Cache(unittest.TestCase):
    def test_simple(self):
        # simple set/get
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")

    def test_add(self):
        # test add (only add if key isn't already in cache)
        cache.add("addkey1", "value")
        cache.add("addkey1", "newvalue")
        self.assertEqual(cache.get("addkey1"), "value")

    def test_non_existent(self):
        # get with non-existent keys
        self.assertEqual(cache.get("does_not_exist"), None)
        self.assertEqual(cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # get_many
        cache.set('a', 'a')
        cache.set('b', 'b')
        cache.set('c', 'c')
        cache.set('d', 'd')
        self.assertEqual(cache.get_many(['a', 'c', 'd']), {'a' : 'a', 'c' : 'c', 'd' : 'd'})
        self.assertEqual(cache.get_many(['a', 'b', 'e']), {'a' : 'a', 'b' : 'b'})

    def test_delete(self):
        # delete
        cache.set("key1", "spam")
        cache.set("key2", "eggs")
        self.assertEqual(cache.get("key1"), "spam")
        cache.delete("key1")
        self.assertEqual(cache.get("key1"), None)
        self.assertEqual(cache.get("key2"), "eggs")

    def test_has_key(self):
        # has_key
        cache.set("hello1", "goodbye1")
        self.assertEqual(cache.has_key("hello1"), True)
        self.assertEqual(cache.has_key("goodbye1"), False)

    def test_in(self):
        cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in cache, True)
        self.assertEqual("goodbye2" in cache, False)

    def test_data_types(self):
        stuff = {
            'string'    : 'this is a string',
            'int'       : 42,
            'list'      : [1, 2, 3, 4],
            'tuple'     : (1, 2, 3, 4),
            'dict'      : {'A': 1, 'B' : 2},
            'function'  : f,
            'class'     : C,
        }

    def test_expiration(self):
        # expiration
        cache.set('expire', 'very quickly', 1)
        time.sleep(2)
        self.assertEqual(cache.get("expire"), None)

    def test_unicode(self):
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x' : 1 }
            }
        for (key, value) in stuff.items():
            cache.set(key, value)
            self.assertEqual(cache.get(key), value)

if __name__ == '__main__':
    unittest.main()
