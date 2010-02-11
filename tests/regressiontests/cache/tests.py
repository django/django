# -*- coding: utf-8 -*-

# Unit tests for cache framework
# Uses whatever cache backend is set in the test settings file.

import os
import shutil
import tempfile
import time
import unittest

from django.conf import settings
from django.core import management
from django.core.cache import get_cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.http import HttpResponse, HttpRequest
from django.utils.cache import patch_vary_headers, get_cache_key, learn_cache_key
from django.utils.hashcompat import md5_constructor
from regressiontests.cache.models import Poll, expensive_calculation

# functions/classes for complex data type tests
def f():
    return 42
class C:
    def m(n):
        return 24

class DummyCacheTests(unittest.TestCase):
    # The Dummy cache backend doesn't really behave like a test backend,
    # so it has different test requirements.
    def setUp(self):
        self.cache = get_cache('dummy://')

    def test_simple(self):
        "Dummy cache backend ignores cache set calls"
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), None)

    def test_add(self):
        "Add doesn't do anything in dummy cache backend"
        self.cache.add("addkey1", "value")
        result = self.cache.add("addkey1", "newvalue")
        self.assertEqual(result, True)
        self.assertEqual(self.cache.get("addkey1"), None)

    def test_non_existent(self):
        "Non-existent keys aren't found in the dummy cache backend"
        self.assertEqual(self.cache.get("does_not_exist"), None)
        self.assertEqual(self.cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        "get_many returns nothing for the dummy cache backend"
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {})

    def test_delete(self):
        "Cache deletion is transparently ignored on the dummy cache backend"
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.assertEqual(self.cache.get("key1"), None)
        self.cache.delete("key1")
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_has_key(self):
        "The has_key method doesn't ever return True for the dummy cache backend"
        self.cache.set("hello1", "goodbye1")
        self.assertEqual(self.cache.has_key("hello1"), False)
        self.assertEqual(self.cache.has_key("goodbye1"), False)

    def test_in(self):
        "The in operator doesn't ever return True for the dummy cache backend"
        self.cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in self.cache, False)
        self.assertEqual("goodbye2" in self.cache, False)

    def test_incr(self):
        "Dummy cache values can't be incremented"
        self.cache.set('answer', 42)
        self.assertRaises(ValueError, self.cache.incr, 'answer')
        self.assertRaises(ValueError, self.cache.incr, 'does_not_exist')

    def test_decr(self):
        "Dummy cache values can't be decremented"
        self.cache.set('answer', 42)
        self.assertRaises(ValueError, self.cache.decr, 'answer')
        self.assertRaises(ValueError, self.cache.decr, 'does_not_exist')

    def test_data_types(self):
        "All data types are ignored equally by the dummy cache"
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
        self.assertEqual(self.cache.get("stuff"), None)

    def test_expiration(self):
        "Expiration has no effect on the dummy cache"
        self.cache.set('expire1', 'very quickly', 1)
        self.cache.set('expire2', 'very quickly', 1)
        self.cache.set('expire3', 'very quickly', 1)

        time.sleep(2)
        self.assertEqual(self.cache.get("expire1"), None)

        self.cache.add("expire2", "newvalue")
        self.assertEqual(self.cache.get("expire2"), None)
        self.assertEqual(self.cache.has_key("expire3"), False)

    def test_unicode(self):
        "Unicode values are ignored by the dummy cache"
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x' : 1 }
            }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), None)

    def test_set_many(self):
        "set_many does nothing for the dummy cache backend"
        self.cache.set_many({'a': 1, 'b': 2})

    def test_delete_many(self):
        "delete_many does nothing for the dummy cache backend"
        self.cache.delete_many(['a', 'b'])

    def test_clear(self):
        "clear does nothing for the dummy cache backend"
        self.cache.clear()


class BaseCacheTests(object):
    # A common set of tests to apply to all cache backends
    def tearDown(self):
        self.cache.clear()

    def test_simple(self):
        # Simple cache set/get works
        self.cache.set("key", "value")
        self.assertEqual(self.cache.get("key"), "value")

    def test_add(self):
        # A key can be added to a cache
        self.cache.add("addkey1", "value")
        result = self.cache.add("addkey1", "newvalue")
        self.assertEqual(result, False)
        self.assertEqual(self.cache.get("addkey1"), "value")

    def test_non_existent(self):
        # Non-existent cache keys return as None/default
        # get with non-existent keys
        self.assertEqual(self.cache.get("does_not_exist"), None)
        self.assertEqual(self.cache.get("does_not_exist", "bang!"), "bang!")

    def test_get_many(self):
        # Multiple cache keys can be returned using get_many
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {'a' : 'a', 'c' : 'c', 'd' : 'd'})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {'a' : 'a', 'b' : 'b'})

    def test_delete(self):
        # Cache keys can be deleted
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.assertEqual(self.cache.get("key1"), "spam")
        self.cache.delete("key1")
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_has_key(self):
        # The cache can be inspected for cache keys
        self.cache.set("hello1", "goodbye1")
        self.assertEqual(self.cache.has_key("hello1"), True)
        self.assertEqual(self.cache.has_key("goodbye1"), False)

    def test_in(self):
        # The in operator can be used to inspet cache contents
        self.cache.set("hello2", "goodbye2")
        self.assertEqual("hello2" in self.cache, True)
        self.assertEqual("goodbye2" in self.cache, False)

    def test_incr(self):
        # Cache values can be incremented
        self.cache.set('answer', 41)
        self.assertEqual(self.cache.incr('answer'), 42)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.incr('answer', 10), 52)
        self.assertEqual(self.cache.get('answer'), 52)
        self.assertRaises(ValueError, self.cache.incr, 'does_not_exist')

    def test_decr(self):
        # Cache values can be decremented
        self.cache.set('answer', 43)
        self.assertEqual(self.cache.decr('answer'), 42)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.decr('answer', 10), 32)
        self.assertEqual(self.cache.get('answer'), 32)
        self.assertRaises(ValueError, self.cache.decr, 'does_not_exist')

    def test_data_types(self):
        # Many different data types can be cached
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

    def test_cache_read_for_model_instance(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="Well?")
        self.assertEqual(Poll.objects.count(), 1)
        pub_date = my_poll.pub_date
        self.cache.set('question', my_poll)
        cached_poll = self.cache.get('question')
        self.assertEqual(cached_poll.pub_date, pub_date)
        # We only want the default expensive calculation run once
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_write_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache write
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.assertEqual(expensive_calculation.num_runs, 1)
        self.cache.set('deferred_queryset', defer_qs)
        # cache set should not re-evaluate default functions
        self.assertEqual(expensive_calculation.num_runs, 1)

    def test_cache_read_for_model_instance_with_deferred(self):
        # Don't want fields with callable as default to be called on cache read
        expensive_calculation.num_runs = 0
        Poll.objects.all().delete()
        my_poll = Poll.objects.create(question="What?")
        self.assertEqual(expensive_calculation.num_runs, 1)
        defer_qs = Poll.objects.all().defer('question')
        self.assertEqual(defer_qs.count(), 1)
        self.cache.set('deferred_queryset', defer_qs)
        self.assertEqual(expensive_calculation.num_runs, 1)
        runs_before_cache_read = expensive_calculation.num_runs
        cached_polls = self.cache.get('deferred_queryset')
        # We only want the default expensive calculation run on creation and set
        self.assertEqual(expensive_calculation.num_runs, runs_before_cache_read)

    def test_expiration(self):
        # Cache values can be set to expire
        self.cache.set('expire1', 'very quickly', 1)
        self.cache.set('expire2', 'very quickly', 1)
        self.cache.set('expire3', 'very quickly', 1)

        time.sleep(2)
        self.assertEqual(self.cache.get("expire1"), None)

        self.cache.add("expire2", "newvalue")
        self.assertEqual(self.cache.get("expire2"), "newvalue")
        self.assertEqual(self.cache.has_key("expire3"), False)

    def test_unicode(self):
        # Unicode values can be cached
        stuff = {
            u'ascii': u'ascii_value',
            u'unicode_ascii': u'Iñtërnâtiônàlizætiøn1',
            u'Iñtërnâtiônàlizætiøn': u'Iñtërnâtiônàlizætiøn2',
            u'ascii': {u'x' : 1 }
            }
        for (key, value) in stuff.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)

    def test_set_many(self):
        # Multiple keys can be set using set_many
        self.cache.set_many({"key1": "spam", "key2": "eggs"})
        self.assertEqual(self.cache.get("key1"), "spam")
        self.assertEqual(self.cache.get("key2"), "eggs")

    def test_set_many_expiration(self):
        # set_many takes a second ``timeout`` parameter
        self.cache.set_many({"key1": "spam", "key2": "eggs"}, 1)
        time.sleep(2)
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_delete_many(self):
        # Multiple keys can be deleted using delete_many
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.set("key3", "ham")
        self.cache.delete_many(["key1", "key2"])
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)
        self.assertEqual(self.cache.get("key3"), "ham")

    def test_clear(self):
        # The cache can be emptied using clear
        self.cache.set("key1", "spam")
        self.cache.set("key2", "eggs")
        self.cache.clear()
        self.assertEqual(self.cache.get("key1"), None)
        self.assertEqual(self.cache.get("key2"), None)

    def test_long_timeout(self):
        '''
        Using a timeout greater than 30 days makes memcached think
        it is an absolute expiration timestamp instead of a relative
        offset. Test that we honour this convention. Refs #12399.
        '''
        self.cache.set('key1', 'eggs', 60*60*24*30 + 1) #30 days + 1 second
        self.assertEqual(self.cache.get('key1'), 'eggs')

        self.cache.add('key2', 'ham', 60*60*24*30 + 1)
        self.assertEqual(self.cache.get('key2'), 'ham')

        self.cache.set_many({'key3': 'sausage', 'key4': 'lobster bisque'}, 60*60*24*30 + 1)
        self.assertEqual(self.cache.get('key3'), 'sausage')
        self.assertEqual(self.cache.get('key4'), 'lobster bisque')

class DBCacheTests(unittest.TestCase, BaseCacheTests):
    def setUp(self):
        management.call_command('createcachetable', 'test_cache_table', verbosity=0, interactive=False)
        self.cache = get_cache('db://test_cache_table')

    def tearDown(self):
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('DROP TABLE test_cache_table')

class LocMemCacheTests(unittest.TestCase, BaseCacheTests):
    def setUp(self):
        self.cache = get_cache('locmem://')

# memcached backend isn't guaranteed to be available.
# To check the memcached backend, the test settings file will
# need to contain a CACHE_BACKEND setting that points at
# your memcache server.
if settings.CACHE_BACKEND.startswith('memcached://'):
    class MemcachedCacheTests(unittest.TestCase, BaseCacheTests):
        def setUp(self):
            self.cache = get_cache(settings.CACHE_BACKEND)

class FileBasedCacheTests(unittest.TestCase, BaseCacheTests):
    """
    Specific test cases for the file-based cache.
    """
    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.cache = get_cache('file://%s' % self.dirname)

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

    def setUp(self):
        self.path = '/cache/test/'
        self.old_settings_key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.old_middleware_seconds = settings.CACHE_MIDDLEWARE_SECONDS
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = 'settingsprefix'
        settings.CACHE_MIDDLEWARE_SECONDS = 1

    def tearDown(self):
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = self.old_settings_key_prefix
        settings.CACHE_MIDDLEWARE_SECONDS = self.old_middleware_seconds

    def _get_request(self, path):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = request.path_info = "/cache/%s" % path
        return request

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

    def test_get_cache_key(self):
        request = self._get_request(self.path)
        response = HttpResponse()
        key_prefix = 'localprefix'
        # Expect None if no headers have been set yet.
        self.assertEqual(get_cache_key(request), None)
        # Set headers to an empty list.
        learn_cache_key(request, response)
        self.assertEqual(get_cache_key(request), 'views.decorators.cache.cache_page.settingsprefix.a8c87a3d8c44853d7f79474f7ffe4ad5.d41d8cd98f00b204e9800998ecf8427e')
        # Verify that a specified key_prefix is taken in to account.
        learn_cache_key(request, response, key_prefix=key_prefix)
        self.assertEqual(get_cache_key(request, key_prefix=key_prefix), 'views.decorators.cache.cache_page.localprefix.a8c87a3d8c44853d7f79474f7ffe4ad5.d41d8cd98f00b204e9800998ecf8427e')

    def test_learn_cache_key(self):
        request = self._get_request(self.path)
        response = HttpResponse()
        response['Vary'] = 'Pony'
        # Make sure that the Vary header is added to the key hash
        learn_cache_key(request, response)
        self.assertEqual(get_cache_key(request), 'views.decorators.cache.cache_page.settingsprefix.a8c87a3d8c44853d7f79474f7ffe4ad5.d41d8cd98f00b204e9800998ecf8427e')

if __name__ == '__main__':
    unittest.main()
