"""
Unit tests for django.core.cache

If you don't have memcached running on localhost port 11211, the memcached tests
will fail.
"""

from django.core import cache
import unittest
import time

# functions/classes for complex data type tests        
def f():
    return 42
class C:
    def m(n):
        return 24
        
class CacheBackendsTest(unittest.TestCase):
    
    def testBackends(self):
        sc = cache.get_cache('simple://')
        mc = cache.get_cache('memcached://127.0.0.1:11211/')
        self.failUnless(isinstance(sc, cache._SimpleCache))
        self.failUnless(isinstance(mc, cache._MemcachedCache))

    def testInvalidBackends(self):
        self.assertRaises(cache.InvalidCacheBackendError, cache.get_cache, 'nothing://foo/')
        self.assertRaises(cache.InvalidCacheBackendError, cache.get_cache, 'not a uri')
        
    def testDefaultTimeouts(self):
        sc = cache.get_cache('simple:///?timeout=15')
        mc = cache.get_cache('memcached://127.0.0.1:11211/?timeout=15')
        self.assertEquals(sc.default_timeout, 15)
        self.assertEquals(sc.default_timeout, 15)

class SimpleCacheTest(unittest.TestCase):
    
    def setUp(self):
        self.cache = cache.get_cache('simple://')
    
    def testGetSet(self):
        self.cache.set('key', 'value')
        self.assertEqual(self.cache.get('key'), 'value')
        
    def testNonExistantKeys(self):
        self.assertEqual(self.cache.get('does not exist'), None)
        self.assertEqual(self.cache.get('does not exist', 'bang!'), 'bang!')

    def testGetMany(self):
        self.cache.set('a', 'a')
        self.cache.set('b', 'b')
        self.cache.set('c', 'c')
        self.cache.set('d', 'd')
        self.assertEqual(self.cache.get_many(['a', 'c', 'd']), {'a' : 'a', 'c' : 'c', 'd' : 'd'})
        self.assertEqual(self.cache.get_many(['a', 'b', 'e']), {'a' : 'a', 'b' : 'b'})

    def testDelete(self):
        self.cache.set('key1', 'spam')
        self.cache.set('key2', 'eggs')
        self.assertEqual(self.cache.get('key1'), 'spam')
        self.cache.delete('key1')
        self.assertEqual(self.cache.get('key1'), None)
        self.assertEqual(self.cache.get('key2'), 'eggs')
        
    def testHasKey(self):
        self.cache.set('hello', 'goodbye')
        self.assertEqual(self.cache.has_key('hello'), True)
        self.assertEqual(self.cache.has_key('goodbye'), False)

    def testDataTypes(self):
        items = {
            'string'    : 'this is a string',
            'int'       : 42,
            'list'      : [1, 2, 3, 4],
            'tuple'     : (1, 2, 3, 4),
            'dict'      : {'A': 1, 'B' : 2},
            'function'  : f,
            'class'     : C,
        }
        for (key, value) in items.items():
            self.cache.set(key, value)
            self.assertEqual(self.cache.get(key), value)
            
    def testExpiration(self):
        self.cache.set('expire', 'very quickly', 1)
        time.sleep(2)
        self.assertEqual(self.cache.get('expire'), None)
        
    def testCull(self):
        c = cache.get_cache('simple://?max_entries=9&cull_frequency=3')
        for i in range(10):
            c.set('culltest%i' % i, i)
        n = 0
        for i in range(10):
            if c.get('culltest%i' % i):
                n += 1
        self.assertEqual(n, 6)
        
    def testCullAll(self):
        c = cache.get_cache('simple://?max_entries=9&cull_frequency=0')
        for i in range(10):
            c.set('cullalltest%i' % i, i)
        for i in range(10):
            self.assertEqual(self.cache.get('cullalltest%i' % i), None)
            
class MemcachedCacheTest(SimpleCacheTest):
    
    def setUp(self):
        self.cache = cache.get_cache('memcached://127.0.0.1:11211/')
        
    testCull = testCullAll = lambda s: None        

def tests():
    s = unittest.TestLoader().loadTestsFromName(__name__)
    unittest.TextTestRunner(verbosity=0).run(s)

if __name__ == "__main__":
    tests()
