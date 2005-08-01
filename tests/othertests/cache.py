# Unit tests for cache framework
# Uses whatever cache backend is set in the test settings file.

from django.core.cache import cache
import time

# functions/classes for complex data type tests        
def f():
    return 42
class C:
    def m(n):
        return 24

# simple set/get
cache.set("key", "value")
assert cache.get("key") == "value"

# get with non-existant keys
assert cache.get("does not exist") is None
assert cache.get("does not exist", "bang!") == "bang!"

# get_many
cache.set('a', 'a')
cache.set('b', 'b')
cache.set('c', 'c')
cache.set('d', 'd')
assert cache.get_many(['a', 'c', 'd']) == {'a' : 'a', 'c' : 'c', 'd' : 'd'}
assert cache.get_many(['a', 'b', 'e']) == {'a' : 'a', 'b' : 'b'}

# delete
cache.set("key1", "spam")
cache.set("key2", "eggs")
assert cache.get("key1") == "spam"
cache.delete("key1")
assert cache.get("key1") is None
assert cache.get("key2") == "eggs"

# has_key
cache.set("hello", "goodbye")
assert cache.has_key("hello") == True
assert cache.has_key("goodbye") == False

# test data types
stuff = {
    'string'    : 'this is a string',
    'int'       : 42,
    'list'      : [1, 2, 3, 4],
    'tuple'     : (1, 2, 3, 4),
    'dict'      : {'A': 1, 'B' : 2},
    'function'  : f,
    'class'     : C,
}
for (key, value) in stuff.items():
    cache.set(key, value)
    assert cache.get(key) == value
    
# expiration
cache.set('expire', 'very quickly', 1)
time.sleep(2)
assert cache.get("expire") == None