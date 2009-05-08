"""
###################
# Empty QueryDict #
###################

>>> q = QueryDict('')

>>> q['foo']
Traceback (most recent call last):
...
MultiValueDictKeyError: "Key 'foo' not found in <QueryDict: {}>"

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
MultiValueDictKeyError: "Key 'foo' not found in <QueryDict: {}>"

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
MultiValueDictKeyError: "Key 'bar' not found in <QueryDict: {u'foo': [u'bar']}>"

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


########################
# Pickling a QueryDict #
########################
>>> import pickle
>>> q = QueryDict('')
>>> q1 = pickle.loads(pickle.dumps(q, 2))
>>> q == q1
True
>>> q = QueryDict('a=b&c=d')
>>> q1 = pickle.loads(pickle.dumps(q, 2))
>>> q == q1
True
>>> q = QueryDict('a=b&c=d&a=1') 
>>> q1 = pickle.loads(pickle.dumps(q, 2))
>>> q == q1 
True

######################################
# HttpResponse with Unicode headers  #
######################################

>>> r = HttpResponse()

If we insert a unicode value it will be converted to an ascii
string. This makes sure we comply with the HTTP specifications.

>>> r['value'] = u'test value'
>>> isinstance(r['value'], str)
True

An error is raised When a unicode object with non-ascii is assigned.

>>> r['value'] = u't\xebst value' # doctest:+ELLIPSIS
Traceback (most recent call last):
...
UnicodeEncodeError: ..., HTTP response headers must be in US-ASCII format

The response also converts unicode keys to strings.

>>> r[u'test'] = 'testing key'
>>> l = list(r.items())
>>> l.sort()
>>> l[1]
('test', 'testing key')

It will also raise errors for keys with non-ascii data.

>>> r[u't\xebst'] = 'testing key'  # doctest:+ELLIPSIS
Traceback (most recent call last):
...
UnicodeEncodeError: ..., HTTP response headers must be in US-ASCII format

# Bug #10188: Do not allow newlines in headers (CR or LF)
>>> r['test\\rstr'] = 'test'
Traceback (most recent call last):
...
BadHeaderError: Header values can't contain newlines (got 'test\\rstr')

>>> r['test\\nstr'] = 'test'
Traceback (most recent call last):
...
BadHeaderError: Header values can't contain newlines (got 'test\\nstr')

#
# Regression test for #8278: QueryDict.update(QueryDict)
#
>>> x = QueryDict("a=1&a=2", mutable=True)
>>> y = QueryDict("a=3&a=4")
>>> x.update(y)
>>> x.getlist('a')
[u'1', u'2', u'3', u'4']
"""

from django.http import QueryDict, HttpResponse

if __name__ == "__main__":
    import doctest
    doctest.testmod()
