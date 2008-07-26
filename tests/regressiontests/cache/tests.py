# -*- coding: utf-8 -*-

# Unit tests for cache framework
# Uses whatever cache backend is set in the test settings file.

import time
import unittest
from django.core.cache import cache
from django.utils.cache import patch_vary_headers
from django.http import HttpResponse

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
        cache.set("empty", 'fred')
        self.assertEqual(cache.has_key("empty"), True)

    def test_in(self):
        cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in cache, True)
        self.assertEqual("goodbye2" in cache, False)
        cache.set("empty", 'fred')
        self.assertEqual("empty" in cache, True)

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
        cache.set("stuff", stuff)
        self.assertEqual(cache.get("stuff"), stuff)

    def test_expiration(self):
        cache.set('expire1', 'very quickly', 1)
        cache.set('expire2', 'very quickly', 1)
        cache.set('expire3', 'very quickly', 1)

        time.sleep(2)        
        self.assertEqual(cache.get("expire1"), None)
        
        cache.add("expire2", "newvalue")
        self.assertEqual(cache.get("expire2"), "newvalue")
        self.assertEqual(cache.has_key("expire3"), False)

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

import os
import md5
import shutil
import tempfile
from django.core.cache.backends.filebased import CacheClass as FileCache

class FileBasedCacheTests(unittest.TestCase):
    """
    Specific test cases for the file-based cache.
    """
    def setUp(self):
        self.dirname = tempfile.mktemp()
        os.mkdir(self.dirname)
        self.cache = FileCache(self.dirname, {})
        
    def tearDown(self):
        shutil.rmtree(self.dirname)
        
    def test_hashing(self):
        """Test that keys are hashed into subdirectories correctly"""
        self.cache.set("foo", "bar")
        keyhash = md5.new("foo").hexdigest()
        keypath = os.path.join(self.dirname, keyhash[:2], keyhash[2:4], keyhash[4:])
        self.assert_(os.path.exists(keypath))
        
    def test_subdirectory_removal(self):
        """
        Make sure that the created subdirectories are correctly removed when empty.
        """
        self.cache.set("foo", "bar")
        keyhash = md5.new("foo").hexdigest()
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
