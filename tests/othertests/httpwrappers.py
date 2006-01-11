"""
###################
# Empty QueryDict #
###################

>>> q = QueryDict('')

>>> q['foo']
Traceback (most recent call last):
...
MultiValueDictKeyError: "Key 'foo' not found in <MultiValueDict: {}>"

>>> q['something'] = 'bar'
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.get('foo', 'default')
'default'

>>> q.getlist('foo')
[]

>>> q.setlist('foo', ['bar', 'baz'])
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.appendlist('foo', ['bar'])
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.has_key('foo')
False

>>> q.items()
[]

>>> q.lists()
[]

>>> q.keys()
[]

>>> q.values()
[]

>>> len(q)
0

>>> q.update({'foo': 'bar'})
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.pop('foo')
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.popitem()
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.clear()
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.setdefault('foo', 'bar')
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.urlencode()
''

###################################
# Mutable copy of empty QueryDict #
###################################

>>> q = q.copy()

>>> q['foo']
Traceback (most recent call last):
...
MultiValueDictKeyError: "Key 'foo' not found in <MultiValueDict: {}>"

>>> q['name'] = 'john'

>>> q['name']
'john'

>>> q.get('foo', 'default')
'default'

>>> q.get('name', 'default')
'john'

>>> q.getlist('name')
['john']

>>> q.getlist('foo')
[]

>>> q.setlist('foo', ['bar', 'baz'])

>>> q.get('foo', 'default')
'baz'

>>> q.getlist('foo')
['bar', 'baz']

>>> q.appendlist('foo', 'another')

>>> q.getlist('foo')
['bar', 'baz', 'another']

>>> q['foo']
'another'

>>> q.has_key('foo')
True

>>> q.items()
[('foo', 'another'), ('name', 'john')]

>>> q.lists()
[('foo', ['bar', 'baz', 'another']), ('name', ['john'])]

>>> q.keys()
['foo', 'name']

>>> q.values()
['another', 'john']

>>> len(q)
2

>>> q.update({'foo': 'hello'})

# Displays last value
>>> q['foo']
'hello'

>>> q.get('foo', 'not available')
'hello'

>>> q.getlist('foo')
['bar', 'baz', 'another', 'hello']

>>> q.pop('foo')
['bar', 'baz', 'another', 'hello']

>>> q.get('foo', 'not there')
'not there'

>>> q.setdefault('foo', 'bar')
'bar'

>>> q['foo']
'bar'

>>> q.getlist('foo')
['bar']

>>> q.urlencode()
'foo=bar&name=john'

>>> q.clear()

>>> len(q)
0

#####################################
# QueryDict with one key/value pair #
#####################################

>>> q = QueryDict('foo=bar')

>>> q['foo']
'bar'

>>> q['bar']
Traceback (most recent call last):
...
MultiValueDictKeyError: "Key 'bar' not found in <MultiValueDict: {'foo': ['bar']}>"

>>> q['something'] = 'bar'
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.get('foo', 'default')
'bar'

>>> q.get('bar', 'default')
'default'

>>> q.getlist('foo')
['bar']

>>> q.getlist('bar')
[]

>>> q.setlist('foo', ['bar', 'baz'])
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.appendlist('foo', ['bar'])
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.has_key('foo')
True

>>> q.has_key('bar')
False

>>> q.items()
[('foo', 'bar')]

>>> q.lists()
[('foo', ['bar'])]

>>> q.keys()
['foo']

>>> q.values()
['bar']

>>> len(q)
1

>>> q.update({'foo': 'bar'})
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.pop('foo')
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.popitem()
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.clear()
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.setdefault('foo', 'bar')
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.urlencode()
'foo=bar'

#####################################################
# QueryDict with two key/value pairs with same keys #
#####################################################

>>> q = QueryDict('vote=yes&vote=no')

>>> q['vote']
'no'

>>> q['something'] = 'bar'
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.get('vote', 'default')
'no'

>>> q.get('foo', 'default')
'default'

>>> q.getlist('vote')
['yes', 'no']

>>> q.getlist('foo')
[]

>>> q.setlist('foo', ['bar', 'baz'])
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.appendlist('foo', ['bar'])
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.has_key('vote')
True

>>> q.has_key('foo')
False

>>> q.items()
[('vote', 'no')]

>>> q.lists()
[('vote', ['yes', 'no'])]

>>> q.keys()
['vote']

>>> q.values()
['no']

>>> len(q)
1

>>> q.update({'foo': 'bar'})
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.pop('foo')
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.popitem()
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.clear()
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.setdefault('foo', 'bar')
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.urlencode()
'vote=yes&vote=no'

"""

from django.http import QueryDict

if __name__ == "__main__":
    import doctest
    doctest.testmod()
