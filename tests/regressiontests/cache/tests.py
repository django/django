# -*- coding: utf-8 -*-

# Unit tests for cache framework
# Uses whatever cache backend is set in the test settings file.

import os
import tempfile
import time
import warnings

from django.conf import settings
from django.core import management
from django.core.cache import get_cache, DEFAULT_CACHE_ALIAS
from django.core.cache.backends.base import CacheKeyWarning
from django.http import HttpResponse, HttpRequest
from django.middleware.cache import FetchFromCacheMiddleware, UpdateCacheMiddleware, CacheMiddleware
from django.test import RequestFactory
from django.test.utils import get_warnings_state, restore_warnings_state
from django.utils import translation
from django.utils import unittest
from django.utils.cache import patch_vary_headers, get_cache_key, learn_cache_key
from django.utils.hashcompat import md5_constructor
from django.views.decorators.cache import cache_page

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
        self.cache = get_cache('django.core.cache.backends.dummy.DummyCache')

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

    def test_incr_version(self):
        "Dummy cache versions can't be incremented"
        self.cache.set('answer', 42)
        self.assertRaises(ValueError, self.cache.incr_version, 'answer')
        self.assertRaises(ValueError, self.cache.incr_version, 'does_not_exist')

    def test_decr_version(self):
        "Dummy cache versions can't be decremented"
        self.cache.set('answer', 42)
        self.assertRaises(ValueError, self.cache.decr_version, 'answer')
        self.assertRaises(ValueError, self.cache.decr_version, 'does_not_exist')


class BaseCacheTests(object):
    # A common set of tests to apply to all cache backends

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

    def test_prefix(self):
        # Test for same cache key conflicts between shared backend
        self.cache.set('somekey', 'value')

        # should not be set in the prefixed cache
        self.assertFalse(self.prefix_cache.has_key('somekey'))

        self.prefix_cache.set('somekey', 'value2')

        self.assertEqual(self.cache.get('somekey'), 'value')
        self.assertEqual(self.prefix_cache.get('somekey'), 'value2')

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

    def test_binary_string(self):
        # Binary strings should be cachable
        from zlib import compress, decompress
        value = 'value_to_be_compressed'
        compressed_value = compress(value)
        self.cache.set('binary1', compressed_value)
        compressed_result = self.cache.get('binary1')
        self.assertEqual(compressed_value, compressed_result)
        self.assertEqual(value, decompress(compressed_result))

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

    def perform_cull_test(self, initial_count, final_count):
        """This is implemented as a utility method, because only some of the backends
        implement culling. The culling algorithm also varies slightly, so the final
        number of entries will vary between backends"""
        # Create initial cache key entries. This will overflow the cache, causing a cull
        for i in range(1, initial_count):
            self.cache.set('cull%d' % i, 'value', 1000)
        count = 0
        # Count how many keys are left in the cache.
        for i in range(1, initial_count):
            if self.cache.has_key('cull%d' % i):
                count = count + 1
        self.assertEqual(count, final_count)

    def test_invalid_keys(self):
        """
        All the builtin backends (except memcached, see below) should warn on
        keys that would be refused by memcached. This encourages portable
        caching code without making it too difficult to use production backends
        with more liberal key rules. Refs #6447.

        """
        # mimic custom ``make_key`` method being defined since the default will
        # never show the below warnings
        def func(key, *args):
            return key

        old_func = self.cache.key_func
        self.cache.key_func = func
        # On Python 2.6+ we could use the catch_warnings context
        # manager to test this warning nicely. Since we can't do that
        # yet, the cleanest option is to temporarily ask for
        # CacheKeyWarning to be raised as an exception.
        _warnings_state = get_warnings_state()
        warnings.simplefilter("error", CacheKeyWarning)

        try:
            # memcached does not allow whitespace or control characters in keys
            self.assertRaises(CacheKeyWarning, self.cache.set, 'key with spaces', 'value')
            # memcached limits key length to 250
            self.assertRaises(CacheKeyWarning, self.cache.set, 'a' * 251, 'value')
        finally:
            restore_warnings_state(_warnings_state)
            self.cache.key_func = old_func

    def test_cache_versioning_get_set(self):
        # set, using default version = 1
        self.cache.set('answer1', 42)
        self.assertEqual(self.cache.get('answer1'), 42)
        self.assertEqual(self.cache.get('answer1', version=1), 42)
        self.assertEqual(self.cache.get('answer1', version=2), None)

        self.assertEqual(self.v2_cache.get('answer1'), None)
        self.assertEqual(self.v2_cache.get('answer1', version=1), 42)
        self.assertEqual(self.v2_cache.get('answer1', version=2), None)

        # set, default version = 1, but manually override version = 2
        self.cache.set('answer2', 42, version=2)
        self.assertEqual(self.cache.get('answer2'), None)
        self.assertEqual(self.cache.get('answer2', version=1), None)
        self.assertEqual(self.cache.get('answer2', version=2), 42)

        self.assertEqual(self.v2_cache.get('answer2'), 42)
        self.assertEqual(self.v2_cache.get('answer2', version=1), None)
        self.assertEqual(self.v2_cache.get('answer2', version=2), 42)

        # v2 set, using default version = 2
        self.v2_cache.set('answer3', 42)
        self.assertEqual(self.cache.get('answer3'), None)
        self.assertEqual(self.cache.get('answer3', version=1), None)
        self.assertEqual(self.cache.get('answer3', version=2), 42)

        self.assertEqual(self.v2_cache.get('answer3'), 42)
        self.assertEqual(self.v2_cache.get('answer3', version=1), None)
        self.assertEqual(self.v2_cache.get('answer3', version=2), 42)

        # v2 set, default version = 2, but manually override version = 1
        self.v2_cache.set('answer4', 42, version=1)
        self.assertEqual(self.cache.get('answer4'), 42)
        self.assertEqual(self.cache.get('answer4', version=1), 42)
        self.assertEqual(self.cache.get('answer4', version=2), None)

        self.assertEqual(self.v2_cache.get('answer4'), None)
        self.assertEqual(self.v2_cache.get('answer4', version=1), 42)
        self.assertEqual(self.v2_cache.get('answer4', version=2), None)

    def test_cache_versioning_add(self):

        # add, default version = 1, but manually override version = 2
        self.cache.add('answer1', 42, version=2)
        self.assertEqual(self.cache.get('answer1', version=1), None)
        self.assertEqual(self.cache.get('answer1', version=2), 42)

        self.cache.add('answer1', 37, version=2)
        self.assertEqual(self.cache.get('answer1', version=1), None)
        self.assertEqual(self.cache.get('answer1', version=2), 42)

        self.cache.add('answer1', 37, version=1)
        self.assertEqual(self.cache.get('answer1', version=1), 37)
        self.assertEqual(self.cache.get('answer1', version=2), 42)

        # v2 add, using default version = 2
        self.v2_cache.add('answer2', 42)
        self.assertEqual(self.cache.get('answer2', version=1), None)
        self.assertEqual(self.cache.get('answer2', version=2), 42)

        self.v2_cache.add('answer2', 37)
        self.assertEqual(self.cache.get('answer2', version=1), None)
        self.assertEqual(self.cache.get('answer2', version=2), 42)

        self.v2_cache.add('answer2', 37, version=1)
        self.assertEqual(self.cache.get('answer2', version=1), 37)
        self.assertEqual(self.cache.get('answer2', version=2), 42)

        # v2 add, default version = 2, but manually override version = 1
        self.v2_cache.add('answer3', 42, version=1)
        self.assertEqual(self.cache.get('answer3', version=1), 42)
        self.assertEqual(self.cache.get('answer3', version=2), None)

        self.v2_cache.add('answer3', 37, version=1)
        self.assertEqual(self.cache.get('answer3', version=1), 42)
        self.assertEqual(self.cache.get('answer3', version=2), None)

        self.v2_cache.add('answer3', 37)
        self.assertEqual(self.cache.get('answer3', version=1), 42)
        self.assertEqual(self.cache.get('answer3', version=2), 37)

    def test_cache_versioning_has_key(self):
        self.cache.set('answer1', 42)

        # has_key
        self.assertTrue(self.cache.has_key('answer1'))
        self.assertTrue(self.cache.has_key('answer1', version=1))
        self.assertFalse(self.cache.has_key('answer1', version=2))

        self.assertFalse(self.v2_cache.has_key('answer1'))
        self.assertTrue(self.v2_cache.has_key('answer1', version=1))
        self.assertFalse(self.v2_cache.has_key('answer1', version=2))

    def test_cache_versioning_delete(self):
        self.cache.set('answer1', 37, version=1)
        self.cache.set('answer1', 42, version=2)
        self.cache.delete('answer1')
        self.assertEqual(self.cache.get('answer1', version=1), None)
        self.assertEqual(self.cache.get('answer1', version=2), 42)

        self.cache.set('answer2', 37, version=1)
        self.cache.set('answer2', 42, version=2)
        self.cache.delete('answer2', version=2)
        self.assertEqual(self.cache.get('answer2', version=1), 37)
        self.assertEqual(self.cache.get('answer2', version=2), None)

        self.cache.set('answer3', 37, version=1)
        self.cache.set('answer3', 42, version=2)
        self.v2_cache.delete('answer3')
        self.assertEqual(self.cache.get('answer3', version=1), 37)
        self.assertEqual(self.cache.get('answer3', version=2), None)

        self.cache.set('answer4', 37, version=1)
        self.cache.set('answer4', 42, version=2)
        self.v2_cache.delete('answer4', version=1)
        self.assertEqual(self.cache.get('answer4', version=1), None)
        self.assertEqual(self.cache.get('answer4', version=2), 42)

    def test_cache_versioning_incr_decr(self):
        self.cache.set('answer1', 37, version=1)
        self.cache.set('answer1', 42, version=2)
        self.cache.incr('answer1')
        self.assertEqual(self.cache.get('answer1', version=1), 38)
        self.assertEqual(self.cache.get('answer1', version=2), 42)
        self.cache.decr('answer1')
        self.assertEqual(self.cache.get('answer1', version=1), 37)
        self.assertEqual(self.cache.get('answer1', version=2), 42)

        self.cache.set('answer2', 37, version=1)
        self.cache.set('answer2', 42, version=2)
        self.cache.incr('answer2', version=2)
        self.assertEqual(self.cache.get('answer2', version=1), 37)
        self.assertEqual(self.cache.get('answer2', version=2), 43)
        self.cache.decr('answer2', version=2)
        self.assertEqual(self.cache.get('answer2', version=1), 37)
        self.assertEqual(self.cache.get('answer2', version=2), 42)

        self.cache.set('answer3', 37, version=1)
        self.cache.set('answer3', 42, version=2)
        self.v2_cache.incr('answer3')
        self.assertEqual(self.cache.get('answer3', version=1), 37)
        self.assertEqual(self.cache.get('answer3', version=2), 43)
        self.v2_cache.decr('answer3')
        self.assertEqual(self.cache.get('answer3', version=1), 37)
        self.assertEqual(self.cache.get('answer3', version=2), 42)

        self.cache.set('answer4', 37, version=1)
        self.cache.set('answer4', 42, version=2)
        self.v2_cache.incr('answer4', version=1)
        self.assertEqual(self.cache.get('answer4', version=1), 38)
        self.assertEqual(self.cache.get('answer4', version=2), 42)
        self.v2_cache.decr('answer4', version=1)
        self.assertEqual(self.cache.get('answer4', version=1), 37)
        self.assertEqual(self.cache.get('answer4', version=2), 42)

    def test_cache_versioning_get_set_many(self):
        # set, using default version = 1
        self.cache.set_many({'ford1': 37, 'arthur1': 42})
        self.assertEqual(self.cache.get_many(['ford1','arthur1']),
                         {'ford1': 37, 'arthur1': 42})
        self.assertEqual(self.cache.get_many(['ford1','arthur1'], version=1),
                         {'ford1': 37, 'arthur1': 42})
        self.assertEqual(self.cache.get_many(['ford1','arthur1'], version=2), {})

        self.assertEqual(self.v2_cache.get_many(['ford1','arthur1']), {})
        self.assertEqual(self.v2_cache.get_many(['ford1','arthur1'], version=1),
                         {'ford1': 37, 'arthur1': 42})
        self.assertEqual(self.v2_cache.get_many(['ford1','arthur1'], version=2), {})

        # set, default version = 1, but manually override version = 2
        self.cache.set_many({'ford2': 37, 'arthur2': 42}, version=2)
        self.assertEqual(self.cache.get_many(['ford2','arthur2']), {})
        self.assertEqual(self.cache.get_many(['ford2','arthur2'], version=1), {})
        self.assertEqual(self.cache.get_many(['ford2','arthur2'], version=2),
                         {'ford2': 37, 'arthur2': 42})

        self.assertEqual(self.v2_cache.get_many(['ford2','arthur2']),
                         {'ford2': 37, 'arthur2': 42})
        self.assertEqual(self.v2_cache.get_many(['ford2','arthur2'], version=1), {})
        self.assertEqual(self.v2_cache.get_many(['ford2','arthur2'], version=2),
                         {'ford2': 37, 'arthur2': 42})

        # v2 set, using default version = 2
        self.v2_cache.set_many({'ford3': 37, 'arthur3': 42})
        self.assertEqual(self.cache.get_many(['ford3','arthur3']), {})
        self.assertEqual(self.cache.get_many(['ford3','arthur3'], version=1), {})
        self.assertEqual(self.cache.get_many(['ford3','arthur3'], version=2),
                         {'ford3': 37, 'arthur3': 42})

        self.assertEqual(self.v2_cache.get_many(['ford3','arthur3']),
                         {'ford3': 37, 'arthur3': 42})
        self.assertEqual(self.v2_cache.get_many(['ford3','arthur3'], version=1), {})
        self.assertEqual(self.v2_cache.get_many(['ford3','arthur3'], version=2),
                         {'ford3': 37, 'arthur3': 42})

        # v2 set, default version = 2, but manually override version = 1
        self.v2_cache.set_many({'ford4': 37, 'arthur4': 42}, version=1)
        self.assertEqual(self.cache.get_many(['ford4','arthur4']),
                         {'ford4': 37, 'arthur4': 42})
        self.assertEqual(self.cache.get_many(['ford4','arthur4'], version=1),
                         {'ford4': 37, 'arthur4': 42})
        self.assertEqual(self.cache.get_many(['ford4','arthur4'], version=2), {})

        self.assertEqual(self.v2_cache.get_many(['ford4','arthur4']), {})
        self.assertEqual(self.v2_cache.get_many(['ford4','arthur4'], version=1),
                         {'ford4': 37, 'arthur4': 42})
        self.assertEqual(self.v2_cache.get_many(['ford4','arthur4'], version=2), {})

    def test_incr_version(self):
        self.cache.set('answer', 42, version=2)
        self.assertEqual(self.cache.get('answer'), None)
        self.assertEqual(self.cache.get('answer', version=1), None)
        self.assertEqual(self.cache.get('answer', version=2), 42)
        self.assertEqual(self.cache.get('answer', version=3), None)

        self.assertEqual(self.cache.incr_version('answer', version=2), 3)
        self.assertEqual(self.cache.get('answer'), None)
        self.assertEqual(self.cache.get('answer', version=1), None)
        self.assertEqual(self.cache.get('answer', version=2), None)
        self.assertEqual(self.cache.get('answer', version=3), 42)

        self.v2_cache.set('answer2', 42)
        self.assertEqual(self.v2_cache.get('answer2'), 42)
        self.assertEqual(self.v2_cache.get('answer2', version=1), None)
        self.assertEqual(self.v2_cache.get('answer2', version=2), 42)
        self.assertEqual(self.v2_cache.get('answer2', version=3), None)

        self.assertEqual(self.v2_cache.incr_version('answer2'), 3)
        self.assertEqual(self.v2_cache.get('answer2'), None)
        self.assertEqual(self.v2_cache.get('answer2', version=1), None)
        self.assertEqual(self.v2_cache.get('answer2', version=2), None)
        self.assertEqual(self.v2_cache.get('answer2', version=3), 42)

        self.assertRaises(ValueError, self.cache.incr_version, 'does_not_exist')

    def test_decr_version(self):
        self.cache.set('answer', 42, version=2)
        self.assertEqual(self.cache.get('answer'), None)
        self.assertEqual(self.cache.get('answer', version=1), None)
        self.assertEqual(self.cache.get('answer', version=2), 42)

        self.assertEqual(self.cache.decr_version('answer', version=2), 1)
        self.assertEqual(self.cache.get('answer'), 42)
        self.assertEqual(self.cache.get('answer', version=1), 42)
        self.assertEqual(self.cache.get('answer', version=2), None)

        self.v2_cache.set('answer2', 42)
        self.assertEqual(self.v2_cache.get('answer2'), 42)
        self.assertEqual(self.v2_cache.get('answer2', version=1), None)
        self.assertEqual(self.v2_cache.get('answer2', version=2), 42)

        self.assertEqual(self.v2_cache.decr_version('answer2'), 1)
        self.assertEqual(self.v2_cache.get('answer2'), None)
        self.assertEqual(self.v2_cache.get('answer2', version=1), 42)
        self.assertEqual(self.v2_cache.get('answer2', version=2), None)

        self.assertRaises(ValueError, self.cache.decr_version, 'does_not_exist', version=2)

    def test_custom_key_func(self):
        # Two caches with different key functions aren't visible to each other
        self.cache.set('answer1', 42)
        self.assertEqual(self.cache.get('answer1'), 42)
        self.assertEqual(self.custom_key_cache.get('answer1'), None)
        self.assertEqual(self.custom_key_cache2.get('answer1'), None)

        self.custom_key_cache.set('answer2', 42)
        self.assertEqual(self.cache.get('answer2'), None)
        self.assertEqual(self.custom_key_cache.get('answer2'), 42)
        self.assertEqual(self.custom_key_cache2.get('answer2'), 42)

def custom_key_func(key, key_prefix, version):
    "A customized cache key function"
    return 'CUSTOM-' + '-'.join([key_prefix, str(version), key])

class DBCacheTests(unittest.TestCase, BaseCacheTests):
    def setUp(self):
        # Spaces are used in the table name to ensure quoting/escaping is working
        self._table_name = 'test cache table'
        management.call_command('createcachetable', self._table_name, verbosity=0, interactive=False)
        self.cache = get_cache('django.core.cache.backends.db.DatabaseCache', LOCATION=self._table_name, OPTIONS={'MAX_ENTRIES': 30})
        self.prefix_cache = get_cache('django.core.cache.backends.db.DatabaseCache', LOCATION=self._table_name, KEY_PREFIX='cacheprefix')
        self.v2_cache = get_cache('django.core.cache.backends.db.DatabaseCache', LOCATION=self._table_name, VERSION=2)
        self.custom_key_cache = get_cache('django.core.cache.backends.db.DatabaseCache', LOCATION=self._table_name, KEY_FUNCTION=custom_key_func)
        self.custom_key_cache2 = get_cache('django.core.cache.backends.db.DatabaseCache', LOCATION=self._table_name, KEY_FUNCTION='regressiontests.cache.tests.custom_key_func')

    def tearDown(self):
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('DROP TABLE %s' % connection.ops.quote_name(self._table_name))

    def test_cull(self):
        self.perform_cull_test(50, 29)

    def test_zero_cull(self):
        self.cache = get_cache('django.core.cache.backends.db.DatabaseCache', LOCATION=self._table_name, OPTIONS={'MAX_ENTRIES': 30, 'CULL_FREQUENCY': 0})
        self.perform_cull_test(50, 18)

    def test_old_initialization(self):
        self.cache = get_cache('db://%s?max_entries=30&cull_frequency=0' % self._table_name)
        self.perform_cull_test(50, 18)

class LocMemCacheTests(unittest.TestCase, BaseCacheTests):
    def setUp(self):
        self.cache = get_cache('django.core.cache.backends.locmem.LocMemCache', OPTIONS={'MAX_ENTRIES': 30})
        self.prefix_cache = get_cache('django.core.cache.backends.locmem.LocMemCache', KEY_PREFIX='cacheprefix')
        self.v2_cache = get_cache('django.core.cache.backends.locmem.LocMemCache', VERSION=2)
        self.custom_key_cache = get_cache('django.core.cache.backends.locmem.LocMemCache', OPTIONS={'MAX_ENTRIES': 30}, KEY_FUNCTION=custom_key_func)
        self.custom_key_cache2 = get_cache('django.core.cache.backends.locmem.LocMemCache', OPTIONS={'MAX_ENTRIES': 30}, KEY_FUNCTION='regressiontests.cache.tests.custom_key_func')

        # LocMem requires a hack to make the other caches
        # share a data store with the 'normal' cache.
        self.prefix_cache._cache = self.cache._cache
        self.prefix_cache._expire_info = self.cache._expire_info

        self.v2_cache._cache = self.cache._cache
        self.v2_cache._expire_info = self.cache._expire_info

        self.custom_key_cache._cache = self.cache._cache
        self.custom_key_cache._expire_info = self.cache._expire_info

        self.custom_key_cache2._cache = self.cache._cache
        self.custom_key_cache2._expire_info = self.cache._expire_info

    def tearDown(self):
        self.cache.clear()

    def test_cull(self):
        self.perform_cull_test(50, 29)

    def test_zero_cull(self):
        self.cache = get_cache('django.core.cache.backends.locmem.LocMemCache', OPTIONS={'MAX_ENTRIES': 30, 'CULL_FREQUENCY': 0})
        self.perform_cull_test(50, 19)

    def test_old_initialization(self):
        self.cache = get_cache('locmem://?max_entries=30&cull_frequency=0')
        self.perform_cull_test(50, 19)

    def test_multiple_caches(self):
        "Check that multiple locmem caches are isolated"
        mirror_cache = get_cache('django.core.cache.backends.locmem.LocMemCache')
        other_cache = get_cache('django.core.cache.backends.locmem.LocMemCache', LOCATION='other')

        self.cache.set('value1', 42)
        self.assertEquals(mirror_cache.get('value1'), 42)
        self.assertEquals(other_cache.get('value1'), None)

# memcached backend isn't guaranteed to be available.
# To check the memcached backend, the test settings file will
# need to contain a cache backend setting that points at
# your memcache server.
class MemcachedCacheTests(unittest.TestCase, BaseCacheTests):
    def setUp(self):
        name = settings.CACHES[DEFAULT_CACHE_ALIAS]['LOCATION']
        self.cache = get_cache('django.core.cache.backends.memcached.MemcachedCache', LOCATION=name)
        self.prefix_cache = get_cache('django.core.cache.backends.memcached.MemcachedCache', LOCATION=name, KEY_PREFIX='cacheprefix')
        self.v2_cache = get_cache('django.core.cache.backends.memcached.MemcachedCache', LOCATION=name, VERSION=2)
        self.custom_key_cache = get_cache('django.core.cache.backends.memcached.MemcachedCache', LOCATION=name, KEY_FUNCTION=custom_key_func)
        self.custom_key_cache2 = get_cache('django.core.cache.backends.memcached.MemcachedCache', LOCATION=name, KEY_FUNCTION='regressiontests.cache.tests.custom_key_func')

    def tearDown(self):
        self.cache.clear()

    def test_invalid_keys(self):
        """
        On memcached, we don't introduce a duplicate key validation
        step (for speed reasons), we just let the memcached API
        library raise its own exception on bad keys. Refs #6447.

        In order to be memcached-API-library agnostic, we only assert
        that a generic exception of some kind is raised.

        """
        # memcached does not allow whitespace or control characters in keys
        self.assertRaises(Exception, self.cache.set, 'key with spaces', 'value')
        # memcached limits key length to 250
        self.assertRaises(Exception, self.cache.set, 'a' * 251, 'value')

MemcachedCacheTests = unittest.skipUnless(settings.CACHES[DEFAULT_CACHE_ALIAS]['BACKEND'].startswith('django.core.cache.backends.memcached.'), "memcached not available")(MemcachedCacheTests)

class FileBasedCacheTests(unittest.TestCase, BaseCacheTests):
    """
    Specific test cases for the file-based cache.
    """
    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.cache = get_cache('django.core.cache.backends.filebased.FileBasedCache', LOCATION=self.dirname, OPTIONS={'MAX_ENTRIES': 30})
        self.prefix_cache = get_cache('django.core.cache.backends.filebased.FileBasedCache', LOCATION=self.dirname, KEY_PREFIX='cacheprefix')
        self.v2_cache = get_cache('django.core.cache.backends.filebased.FileBasedCache', LOCATION=self.dirname, VERSION=2)
        self.custom_key_cache = get_cache('django.core.cache.backends.filebased.FileBasedCache', LOCATION=self.dirname, KEY_FUNCTION=custom_key_func)
        self.custom_key_cache2 = get_cache('django.core.cache.backends.filebased.FileBasedCache', LOCATION=self.dirname, KEY_FUNCTION='regressiontests.cache.tests.custom_key_func')

    def tearDown(self):
        self.cache.clear()

    def test_hashing(self):
        """Test that keys are hashed into subdirectories correctly"""
        self.cache.set("foo", "bar")
        key = self.cache.make_key("foo")
        keyhash = md5_constructor(key).hexdigest()
        keypath = os.path.join(self.dirname, keyhash[:2], keyhash[2:4], keyhash[4:])
        self.assert_(os.path.exists(keypath))

    def test_subdirectory_removal(self):
        """
        Make sure that the created subdirectories are correctly removed when empty.
        """
        self.cache.set("foo", "bar")
        key = self.cache.make_key("foo")
        keyhash = md5_constructor(key).hexdigest()
        keypath = os.path.join(self.dirname, keyhash[:2], keyhash[2:4], keyhash[4:])
        self.assert_(os.path.exists(keypath))

        self.cache.delete("foo")
        self.assert_(not os.path.exists(keypath))
        self.assert_(not os.path.exists(os.path.dirname(keypath)))
        self.assert_(not os.path.exists(os.path.dirname(os.path.dirname(keypath))))

    def test_cull(self):
        self.perform_cull_test(50, 29)

    def test_old_initialization(self):
        self.cache = get_cache('file://%s?max_entries=30' % self.dirname)
        self.perform_cull_test(50, 29)

class CustomCacheKeyValidationTests(unittest.TestCase):
    """
    Tests for the ability to mixin a custom ``validate_key`` method to
    a custom cache backend that otherwise inherits from a builtin
    backend, and override the default key validation. Refs #6447.

    """
    def test_custom_key_validation(self):
        cache = get_cache('regressiontests.cache.liberal_backend://')

        # this key is both longer than 250 characters, and has spaces
        key = 'some key with spaces' * 15
        val = 'a value'
        cache.set(key, val)
        self.assertEqual(cache.get(key), val)

class CacheUtils(unittest.TestCase):
    """TestCase for django.utils.cache functions."""

    def setUp(self):
        self.path = '/cache/test/'
        self.old_cache_middleware_key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.old_cache_middleware_seconds = settings.CACHE_MIDDLEWARE_SECONDS
        self.orig_use_i18n = settings.USE_I18N
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = 'settingsprefix'
        settings.CACHE_MIDDLEWARE_SECONDS = 1
        settings.USE_I18N = False

    def tearDown(self):
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = self.old_cache_middleware_key_prefix
        settings.CACHE_MIDDLEWARE_SECONDS = self.old_cache_middleware_seconds
        settings.USE_I18N = self.orig_use_i18n

    def _get_request(self, path, method='GET'):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.method = method
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
        self.assertEqual(get_cache_key(request), 'views.decorators.cache.cache_page.settingsprefix.GET.a8c87a3d8c44853d7f79474f7ffe4ad5.d41d8cd98f00b204e9800998ecf8427e')
        # Verify that a specified key_prefix is taken in to account.
        learn_cache_key(request, response, key_prefix=key_prefix)
        self.assertEqual(get_cache_key(request, key_prefix=key_prefix), 'views.decorators.cache.cache_page.localprefix.GET.a8c87a3d8c44853d7f79474f7ffe4ad5.d41d8cd98f00b204e9800998ecf8427e')

    def test_learn_cache_key(self):
        request = self._get_request(self.path, 'HEAD')
        response = HttpResponse()
        response['Vary'] = 'Pony'
        # Make sure that the Vary header is added to the key hash
        learn_cache_key(request, response)
        self.assertEqual(get_cache_key(request), 'views.decorators.cache.cache_page.settingsprefix.HEAD.a8c87a3d8c44853d7f79474f7ffe4ad5.d41d8cd98f00b204e9800998ecf8427e')

class PrefixedCacheUtils(CacheUtils):
    def setUp(self):
        super(PrefixedCacheUtils, self).setUp()
        self.old_cache_key_prefix = settings.CACHES['default'].get('KEY_PREFIX', None)
        settings.CACHES['default']['KEY_PREFIX'] = 'cacheprefix'

    def tearDown(self):
        super(PrefixedCacheUtils, self).tearDown()
        if self.old_cache_key_prefix is None:
            del settings.CACHES['default']['KEY_PREFIX']
        else:
            settings.CACHES['default']['KEY_PREFIX'] = self.old_cache_key_prefix

class CacheHEADTest(unittest.TestCase):

    def setUp(self):
        self.orig_cache_middleware_seconds = settings.CACHE_MIDDLEWARE_SECONDS
        self.orig_cache_middleware_key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.orig_caches = settings.CACHES
        settings.CACHE_MIDDLEWARE_SECONDS = 60
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = 'test'
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
            }
        }
        self.path = '/cache/test/'

    def tearDown(self):
        settings.CACHE_MIDDLEWARE_SECONDS = self.orig_cache_middleware_seconds
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = self.orig_cache_middleware_key_prefix
        settings.CACHES = self.orig_caches

    def _get_request(self, method):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.method = method
        request.path = request.path_info = self.path
        return request

    def _get_request_cache(self, method):
        request = self._get_request(method)
        request._cache_update_cache = True
        return request

    def _set_cache(self, request, msg):
        response = HttpResponse()
        response.content = msg
        return UpdateCacheMiddleware().process_response(request, response)

    def test_head_caches_correctly(self):
        test_content = 'test content'

        request = self._get_request_cache('HEAD')
        self._set_cache(request, test_content)

        request = self._get_request('HEAD')
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        self.assertNotEqual(get_cache_data, None)
        self.assertEqual(test_content, get_cache_data.content)

    def test_head_with_cached_get(self):
        test_content = 'test content'

        request = self._get_request_cache('GET')
        self._set_cache(request, test_content)

        request = self._get_request('HEAD')
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        self.assertNotEqual(get_cache_data, None)
        self.assertEqual(test_content, get_cache_data.content)

class CacheI18nTest(unittest.TestCase):

    def setUp(self):
        self.orig_cache_middleware_seconds = settings.CACHE_MIDDLEWARE_SECONDS
        self.orig_cache_middleware_key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.orig_caches = settings.CACHES
        self.orig_use_i18n = settings.USE_I18N
        self.orig_languages =  settings.LANGUAGES
        settings.LANGUAGES = (
                ('en', 'English'),
                ('es', 'Spanish'),
        )
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = 'settingsprefix'
        self.path = '/cache/test/'

    def tearDown(self):
        settings.CACHE_MIDDLEWARE_SECONDS = self.orig_cache_middleware_seconds
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = self.orig_cache_middleware_key_prefix
        settings.CACHES = self.orig_caches
        settings.USE_I18N = self.orig_use_i18n
        settings.LANGUAGES = self.orig_languages
        translation.deactivate()

    def _get_request(self):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = request.path_info = self.path
        return request

    def _get_request_cache(self):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = request.path_info = self.path
        request._cache_update_cache = True
        request.method = 'GET'
        request.session = {}
        return request

    def test_cache_key_i18n(self):
        settings.USE_I18N = True
        request = self._get_request()
        lang = translation.get_language()
        response = HttpResponse()
        key = learn_cache_key(request, response)
        self.assertTrue(key.endswith(lang), "Cache keys should include the language name when i18n is active")
        key2 = get_cache_key(request)
        self.assertEqual(key, key2)

    def test_cache_key_no_i18n (self):
        settings.USE_I18N = False
        request = self._get_request()
        lang = translation.get_language()
        response = HttpResponse()
        key = learn_cache_key(request, response)
        self.assertFalse(key.endswith(lang), "Cache keys shouldn't include the language name when i18n is inactive")

    def test_middleware(self):
        def set_cache(request, lang, msg):
            translation.activate(lang)
            response = HttpResponse()
            response.content= msg
            return UpdateCacheMiddleware().process_response(request, response)

        settings.CACHE_MIDDLEWARE_SECONDS = 60
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = "test"
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
            }
        }
        settings.USE_ETAGS = True
        settings.USE_I18N = True
        en_message ="Hello world!"
        es_message ="Hola mundo!"

        request = self._get_request_cache()
        set_cache(request, 'en', en_message)
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        # Check that we can recover the cache
        self.assertNotEqual(get_cache_data.content, None)
        self.assertEqual(en_message, get_cache_data.content)
        # Check that we use etags
        self.assertTrue(get_cache_data.has_header('ETag'))
        # Check that we can disable etags
        settings.USE_ETAGS = False
        request._cache_update_cache = True
        set_cache(request, 'en', en_message)
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        self.assertFalse(get_cache_data.has_header('ETag'))
        # change the session language and set content
        request = self._get_request_cache()
        set_cache(request, 'es', es_message)
        # change again the language
        translation.activate('en')
        # retrieve the content from cache
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        self.assertEqual(get_cache_data.content, en_message)
        # change again the language
        translation.activate('es')
        get_cache_data = FetchFromCacheMiddleware().process_request(request)
        self.assertEqual(get_cache_data.content, es_message)

class PrefixedCacheI18nTest(CacheI18nTest):
    def setUp(self):
        super(PrefixedCacheI18nTest, self).setUp()
        self.old_cache_key_prefix = settings.CACHES['default'].get('KEY_PREFIX', None)
        settings.CACHES['default']['KEY_PREFIX'] = 'cacheprefix'

    def tearDown(self):
        super(PrefixedCacheI18nTest, self).tearDown()
        if self.old_cache_key_prefix is not None:
            del settings.CACHES['default']['KEY_PREFIX']
        else:
            settings.CACHES['default']['KEY_PREFIX'] = self.old_cache_key_prefix


def hello_world_view(request, value):
    return HttpResponse('Hello World %s' % value)

class CacheMiddlewareTest(unittest.TestCase):

    def setUp(self):
        self.factory = RequestFactory()

        self.orig_cache_middleware_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.orig_cache_middleware_key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.orig_cache_middleware_seconds = settings.CACHE_MIDDLEWARE_SECONDS
        self.orig_cache_middleware_anonymous_only = getattr(settings, 'CACHE_MIDDLEWARE_ANONYMOUS_ONLY', False)
        self.orig_caches = settings.CACHES

        settings.CACHE_MIDDLEWARE_ALIAS = 'other'
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = 'middlewareprefix'
        settings.CACHE_MIDDLEWARE_SECONDS = 30
        settings.CACHE_MIDDLEWARE_ANONYMOUS_ONLY = False
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
            },
            'other': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'other',
                'TIMEOUT': '1'
            }
        }

    def tearDown(self):
        settings.CACHE_MIDDLEWARE_ALIAS = self.orig_cache_middleware_alias
        settings.CACHE_MIDDLEWARE_KEY_PREFIX = self.orig_cache_middleware_key_prefix
        settings.CACHE_MIDDLEWARE_SECONDS = self.orig_cache_middleware_seconds
        settings.CACHE_MIDDLEWARE_ANONYMOUS_ONLY = self.orig_cache_middleware_anonymous_only
        settings.CACHES = self.orig_caches

    def test_constructor(self):
        """
        Ensure the constructor is correctly distinguishing between usage of CacheMiddleware as
        Middleware vs. usage of CacheMiddleware as view decorator and setting attributes
        appropriately.
        """
        # If no arguments are passed in construction, it's being used as middleware.
        middleware = CacheMiddleware()

        # Now test object attributes against values defined in setUp above
        self.assertEquals(middleware.cache_timeout, 30)
        self.assertEquals(middleware.key_prefix, 'middlewareprefix')
        self.assertEquals(middleware.cache_alias, 'other')
        self.assertEquals(middleware.cache_anonymous_only, False)

        # If arguments are being passed in construction, it's being used as a decorator.
        # First, test with "defaults":
        as_view_decorator = CacheMiddleware(cache_alias=None, key_prefix=None)

        self.assertEquals(as_view_decorator.cache_timeout, 300) # Timeout value for 'default' cache, i.e. 300
        self.assertEquals(as_view_decorator.key_prefix, '')
        self.assertEquals(as_view_decorator.cache_alias, 'default') # Value of DEFAULT_CACHE_ALIAS from django.core.cache
        self.assertEquals(as_view_decorator.cache_anonymous_only, False)

        # Next, test with custom values:
        as_view_decorator_with_custom = CacheMiddleware(cache_anonymous_only=True, cache_timeout=60, cache_alias='other', key_prefix='foo')

        self.assertEquals(as_view_decorator_with_custom.cache_timeout, 60)
        self.assertEquals(as_view_decorator_with_custom.key_prefix, 'foo')
        self.assertEquals(as_view_decorator_with_custom.cache_alias, 'other')
        self.assertEquals(as_view_decorator_with_custom.cache_anonymous_only, True)

    def test_middleware(self):
        middleware = CacheMiddleware()
        prefix_middleware = CacheMiddleware(key_prefix='prefix1')
        timeout_middleware = CacheMiddleware(cache_timeout=1)

        request = self.factory.get('/view/')

        # Put the request through the request middleware
        result = middleware.process_request(request)
        self.assertEquals(result, None)

        response = hello_world_view(request, '1')

        # Now put the response through the response middleware
        response = middleware.process_response(request, response)

        # Repeating the request should result in a cache hit
        result = middleware.process_request(request)
        self.assertNotEquals(result, None)
        self.assertEquals(result.content, 'Hello World 1')

        # The same request through a different middleware won't hit
        result = prefix_middleware.process_request(request)
        self.assertEquals(result, None)

        # The same request with a timeout _will_ hit
        result = timeout_middleware.process_request(request)
        self.assertNotEquals(result, None)
        self.assertEquals(result.content, 'Hello World 1')

    def test_cache_middleware_anonymous_only_wont_cause_session_access(self):
        """ The cache middleware shouldn't cause a session access due to
        CACHE_MIDDLEWARE_ANONYMOUS_ONLY if nothing else has accessed the
        session. Refs 13283 """
        settings.CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.auth.middleware import AuthenticationMiddleware

        middleware = CacheMiddleware()
        session_middleware = SessionMiddleware()
        auth_middleware = AuthenticationMiddleware()

        request = self.factory.get('/view_anon/')

        # Put the request through the request middleware
        session_middleware.process_request(request)
        auth_middleware.process_request(request)
        result = middleware.process_request(request)
        self.assertEquals(result, None)

        response = hello_world_view(request, '1')

        # Now put the response through the response middleware
        session_middleware.process_response(request, response)
        response = middleware.process_response(request, response)

        self.assertEqual(request.session.accessed, False)

    def test_cache_middleware_anonymous_only_with_cache_page(self):
        """CACHE_MIDDLEWARE_ANONYMOUS_ONLY should still be effective when used
        with the cache_page decorator: the response to a request from an
        authenticated user should not be cached."""
        settings.CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

        request = self.factory.get('/view_anon/')

        class MockAuthenticatedUser(object):
            def is_authenticated(self):
                return True

        class MockAccessedSession(object):
            accessed = True

        request.user = MockAuthenticatedUser()
        request.session = MockAccessedSession()

        response = cache_page(hello_world_view)(request, '1')

        self.assertFalse("Cache-Control" in response)

    def test_view_decorator(self):
        # decorate the same view with different cache decorators
        default_view = cache_page(hello_world_view)
        default_with_prefix_view = cache_page(key_prefix='prefix1')(hello_world_view)

        explicit_default_view = cache_page(cache='default')(hello_world_view)
        explicit_default_with_prefix_view = cache_page(cache='default', key_prefix='prefix1')(hello_world_view)

        other_view = cache_page(cache='other')(hello_world_view)
        other_with_prefix_view = cache_page(cache='other', key_prefix='prefix2')(hello_world_view)
        other_with_timeout_view = cache_page(4, cache='other', key_prefix='prefix3')(hello_world_view)

        request = self.factory.get('/view/')

        # Request the view once
        response = default_view(request, '1')
        self.assertEquals(response.content, 'Hello World 1')

        # Request again -- hit the cache
        response = default_view(request, '2')
        self.assertEquals(response.content, 'Hello World 1')

        # Requesting the same view with the explicit cache should yield the same result
        response = explicit_default_view(request, '3')
        self.assertEquals(response.content, 'Hello World 1')

        # Requesting with a prefix will hit a different cache key
        response = explicit_default_with_prefix_view(request, '4')
        self.assertEquals(response.content, 'Hello World 4')

        # Hitting the same view again gives a cache hit
        response = explicit_default_with_prefix_view(request, '5')
        self.assertEquals(response.content, 'Hello World 4')

        # And going back to the implicit cache will hit the same cache
        response = default_with_prefix_view(request, '6')
        self.assertEquals(response.content, 'Hello World 4')

        # Requesting from an alternate cache won't hit cache
        response = other_view(request, '7')
        self.assertEquals(response.content, 'Hello World 7')

        # But a repeated hit will hit cache
        response = other_view(request, '8')
        self.assertEquals(response.content, 'Hello World 7')

        # And prefixing the alternate cache yields yet another cache entry
        response = other_with_prefix_view(request, '9')
        self.assertEquals(response.content, 'Hello World 9')

        # Request from the alternate cache with a new prefix and a custom timeout
        response = other_with_timeout_view(request, '10')
        self.assertEquals(response.content, 'Hello World 10')

        # But if we wait a couple of seconds...
        time.sleep(2)

        # ... the default cache will still hit
        cache = get_cache('default')
        response = default_view(request, '11')
        self.assertEquals(response.content, 'Hello World 1')

        # ... the default cache with a prefix will still hit
        response = default_with_prefix_view(request, '12')
        self.assertEquals(response.content, 'Hello World 4')

        # ... the explicit default cache will still hit
        response = explicit_default_view(request, '13')
        self.assertEquals(response.content, 'Hello World 1')

        # ... the explicit default cache with a prefix will still hit
        response = explicit_default_with_prefix_view(request, '14')
        self.assertEquals(response.content, 'Hello World 4')

        # .. but a rapidly expiring cache won't hit
        response = other_view(request, '15')
        self.assertEquals(response.content, 'Hello World 15')

        # .. even if it has a prefix
        response = other_with_prefix_view(request, '16')
        self.assertEquals(response.content, 'Hello World 16')

        # ... but a view with a custom timeout will still hit
        response = other_with_timeout_view(request, '17')
        self.assertEquals(response.content, 'Hello World 10')

        # And if we wait a few more seconds
        time.sleep(2)

        # the custom timeouot cache will miss
        response = other_with_timeout_view(request, '18')
        self.assertEquals(response.content, 'Hello World 18')

if __name__ == '__main__':
    unittest.main()
