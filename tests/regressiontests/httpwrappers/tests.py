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

>>> 'foo' in q
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
u'john'

>>> del q['name']
>>> 'name' in q
False

>>> q['name'] = 'john'

>>> q.get('foo', 'default')
'default'

>>> q.get('name', 'default')
u'john'

>>> q.getlist('name')
[u'john']

>>> q.getlist('foo')
[]

>>> q.setlist('foo', ['bar', 'baz'])

>>> q.get('foo', 'default')
u'baz'

>>> q.getlist('foo')
[u'bar', u'baz']

>>> q.appendlist('foo', 'another')

>>> q.getlist('foo')
[u'bar', u'baz', u'another']

>>> q['foo']
u'another'

>>> q.has_key('foo')
True

>>> 'foo' in q
True

>>> q.items()
[(u'foo', u'another'), (u'name', u'john')]

>>> q.lists()
[(u'foo', [u'bar', u'baz', u'another']), (u'name', [u'john'])]

>>> q.keys()
[u'foo', u'name']

>>> q.values()
[u'another', u'john']

>>> len(q)
2

>>> q.update({'foo': 'hello'})

# Displays last value
>>> q['foo']
u'hello'

>>> q.get('foo', 'not available')
u'hello'

>>> q.getlist('foo')
[u'bar', u'baz', u'another', u'hello']

>>> q.pop('foo')
[u'bar', u'baz', u'another', u'hello']

>>> q.pop('foo', 'not there')
'not there'

>>> q.get('foo', 'not there')
'not there'

>>> q.setdefault('foo', 'bar')
u'bar'

>>> q['foo']
u'bar'

>>> q.getlist('foo')
[u'bar']

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
u'bar'

>>> q['bar']
Traceback (most recent call last):
...
MultiValueDictKeyError: "Key 'bar' not found in <MultiValueDict: {u'foo': [u'bar']}>"

>>> q['something'] = 'bar'
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.get('foo', 'default')
u'bar'

>>> q.get('bar', 'default')
'default'

>>> q.getlist('foo')
[u'bar']

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

>>> 'foo' in q
True

>>> q.has_key('bar')
False

>>> 'bar' in q
False

>>> q.items()
[(u'foo', u'bar')]

>>> q.lists()
[(u'foo', [u'bar'])]

>>> q.keys()
[u'foo']

>>> q.values()
[u'bar']

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
u'no'

>>> q['something'] = 'bar'
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

>>> q.get('vote', 'default')
u'no'

>>> q.get('foo', 'default')
'default'

>>> q.getlist('vote')
[u'yes', u'no']

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

>>> 'vote' in q
True

>>> q.has_key('foo')
False

>>> 'foo' in q
False

>>> q.items()
[(u'vote', u'no')]

>>> q.lists()
[(u'vote', [u'yes', u'no'])]

>>> q.keys()
[u'vote']

>>> q.values()
[u'no']

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

>>> del q['vote']
Traceback (most recent call last):
...
AttributeError: This QueryDict instance is immutable

# QueryDicts must be able to handle invalid input encoding (in this case, bad
# UTF-8 encoding).
>>> q = QueryDict('foo=bar&foo=\xff')

>>> q['foo']
u'\ufffd'

>>> q.getlist('foo')
[u'bar', u'\ufffd']

"""

from django.http import QueryDict

if __name__ == "__main__":
    import doctest
    doctest.testmod()
