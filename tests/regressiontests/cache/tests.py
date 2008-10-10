# -*- coding: utf-8 -*-

# Unit tests for cache framework
# Uses whatever cache backend is set in the test settings file.

import os
import shutil
import tempfile
import time
import unittest

from django.core.cache import cache, get_cache
from django.core.cache.backends.filebased import CacheClass as FileCache
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers
from django.utils.hashcompat import md5_constructor

# functions/classes for complex data type tests
def f():
    return 42
class C:
    def m(n):
        return 24

class Cache(unittest.TestCase):
    def setUp(self):
        # Special-case the file cache so we can clean up after ourselves.
        if isinstance(cache, FileCache):
            self.cache_dir = tempfile.mkdtemp()
            self.cache = get_cache("file:///%s" % self.cache_dir)
        else:
            self.cache_dir = None
            self.cache = cache
            
    def tearDown(self):
        if self.cache_dir is not None:
            shutil.rmtree(self.cache_dir)
    
    def test_simple(self):
        # simple set/get
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), "value")

    def test_add(self):
        # test add (only add if key isn't already in cache)
        self.cache.add("addkey1", "value")
        result = self.cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(self.cache.get("addkey1"), "value")

    def test_non_existent(self):
        # get with non-existent keys
        self.assertEqual(self.cache.get("does_not_exist"), None)
        self.assertEqual(self.cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # get_many
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {'a' : 'a', 'c' : 'c', 'd' : 'd'})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {'a' : 'a', 'b' : 'b'})

    def test_delete(self):
        # delete
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.assertEqual(self.cache.get("key1"), "spam")
        self.cache.delete("key1")
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_has_key(self):
        # has_key
        self.cache.set("hello1", "goodbye1")
        self.assertEqual(self.cache.has_key("hello1"), True)
        self.assertEqual(self.cache.has_key("goodbye1"), False)

    def test_in(self):
        self.cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in self.cache, True)
        self.assertEqual("goodbye2" in self.cache, False)

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
        self.cache.set("stuff", stuff)
        self.assertEqual(self.cache.get("stuff"), stuff)

    def test_expiration(self):
        self.cache.set('expire1', 'very quickly', 1)
        self.cache.set('expire2', 'very quickly', 1)
        self.cache.set('expire3', 'very quickly', 1)

        time.sleep(2)
        self.assertEqual(self.cache.get("expire1"), None)

        self.cache.add("expire2", "newvalue")
        self.assertEqual(self.cache.get("expire2"), "newvalue")
        self.assertEqual(self.cache.has_key("expire3"), False)

    def test_unicode(self):
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x' : 1 }
            }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)


class FileBasedCacheTests(unittest.TestCase):
    """
    Specific test cases for the file-based cache.
    """
    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.cache = FileCache(self.dirname, {})

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_hashing(self):
        """Test that keys are hashed into subdirectories correctly"""
        self.cache.set("foo", "bar")
        keyhash = md5_constructor("foo").hexdigest()
        keypath = os.path.join(self.dirname, keyhash[:2], keyhash[2:4], keyhash[4:])
        self.assert_(os.path.exists(keypath))

    def test_subdirectory_removal(self):
        """
        Make sure that the created subdirectories are correctly removed when empty.
        """
        self.cache.set("foo", "bar")
        keyhash = md5_constructor("foo").hexdigest()
        keypath = os.path.join(self.dirname, keyhash[:2], keyhash[2:4], keyhash[4:])
        self.assert_(os.path.exists(keypath))

        self.cache.delete("foo")
        self.assert_(not os.path.exists(keypath))
        self.assert_(not os.path.exists(os.path.dirname(keypath)))
        self.assert_(not os.path.exists(os.path.dirname(os.path.dirname(keypath))))

class CacheUtils(unittest.TestCase):
    """TestCase for django.utils.cache functions."""

    def test_patch_vary_headers(self):
        headers = (
            # Initial vary, new headers, resulting vary.
            (None, ('Accept-Encoding',), 'Accept-Encoding'),
            ('Accept-Encoding', ('accept-encoding',), 'Accept-Encoding'),
            ('Accept-Encoding', ('ACCEPT-ENCODING',), 'Accept-Encoding'),
            ('Cookie', ('Accept-Encoding',), 'Cookie, Accept-Encoding'),
            ('Cookie, Accept-Encoding', ('Accept-Encoding',), 'Cookie, Accept-Encoding'),
            ('Cookie, Accept-Encoding', ('Accept-Encoding', 'cookie'), 'Cookie, Accept-Encoding'),
            (None, ('Accept-Encoding', 'COOKIE'), 'Accept-Encoding, COOKIE'),
            ('Cookie,     Accept-Encoding', ('Accept-Encoding', 'cookie'), 'Cookie, Accept-Encoding'),
            ('Cookie    ,     Accept-Encoding', ('Accept-Encoding', 'cookie'), 'Cookie, Accept-Encoding'),
        )
        for initial_vary, newheaders, resulting_vary in headers:
            response = HttpResponse()
            if initial_vary is not None:
                response['Vary'] = initial_vary
            patch_vary_headers(response, newheaders)
            self.assertEqual(response['Vary'], resulting_vary)


if __name__ == '__main__':
    unittest.main()
