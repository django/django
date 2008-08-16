"""
# Tests for stuff in django.utils.datastructures.

>>> from django.utils.datastructures import *

### MergeDict #################################################################

>>> d1 = {'chris':'cool','camri':'cute','cotton':'adorable','tulip':'snuggable', 'twoofme':'firstone'}
>>> d2 = {'chris2':'cool2','camri2':'cute2','cotton2':'adorable2','tulip2':'snuggable2'}
>>> d3 = {'chris3':'cool3','camri3':'cute3','cotton3':'adorable3','tulip3':'snuggable3'}
>>> d4 = {'twoofme':'secondone'}
>>> md = MergeDict( d1,d2,d3 )
>>> md['chris']
'cool'
>>> md['camri']
'cute'
>>> md['twoofme']
'firstone'
>>> md2 = md.copy()
>>> md2['chris']
'cool'

MergeDict can merge MultiValueDicts
>>> multi1 = MultiValueDict({'key1': ['value1'], 'key2': ['value2', 'value3']})
>>> multi2 = MultiValueDict({'key2': ['value4'], 'key4': ['value5', 'value6']})
>>> mm = MergeDict(multi1, multi2)

# Although 'key2' appears in both dictionaries, only the first value is used.
>>> mm.getlist('key2')
['value2', 'value3']
>>> mm.getlist('key4')
['value5', 'value6']
>>> mm.getlist('undefined')
[]

### MultiValueDict ##########################################################

>>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
>>> d['name']
'Simon'
>>> d.get('name')
'Simon'
>>> d.getlist('name')
['Adrian', 'Simon']
>>> list(d.iteritems())
[('position', 'Developer'), ('name', 'Simon')]
>>> d['lastname']
Traceback (most recent call last):
...
MultiValueDictKeyError: "Key 'lastname' not found in <MultiValueDict: {'position': ['Developer'], 'name': ['Adrian', 'Simon']}>"
>>> d.get('lastname')

>>> d.get('lastname', 'nonexistent')
'nonexistent'
>>> d.getlist('lastname')
[]
>>> d.setlist('lastname', ['Holovaty', 'Willison'])
>>> d.getlist('lastname')
['Holovaty', 'Willison']

### SortedDict #################################################################

>>> d = SortedDict()
>>> d['one'] = 'one'
>>> d['two'] = 'two'
>>> d['three'] = 'three'
>>> d['one']
'one'
>>> d['two']
'two'
>>> d['three']
'three'
>>> d.keys()
['one', 'two', 'three']
>>> d.values()
['one', 'two', 'three']
>>> d['one'] = 'not one'
>>> d['one']
'not one'
>>> d.keys() == d.copy().keys()
True
>>> d2 = d.copy()
>>> d2['four'] = 'four'
>>> print repr(d)
{'one': 'not one', 'two': 'two', 'three': 'three'}
>>> d.pop('one', 'missing')
'not one'
>>> d.pop('one', 'missing')
'missing'

We don't know which item will be popped in popitem(), so we'll just check that
the number of keys has decreased.
>>> l = len(d)
>>> _ = d.popitem()
>>> l - len(d)
1

Init from sequence of tuples
>>> d = SortedDict((
... (1, "one"),
... (0, "zero"),
... (2, "two")))
>>> print repr(d)
{1: 'one', 0: 'zero', 2: 'two'}

>>> d.clear()
>>> d
{}
>>> d.keyOrder
[]

### DotExpandedDict ############################################################

>>> d = DotExpandedDict({'person.1.firstname': ['Simon'], 'person.1.lastname': ['Willison'], 'person.2.firstname': ['Adrian'], 'person.2.lastname': ['Holovaty']})
>>> d['person']['1']['lastname']
['Willison']
>>> d['person']['2']['lastname']
['Holovaty']
>>> d['person']['2']['firstname']
['Adrian']

### ImmutableList ################################################################
>>> d = ImmutableList(range(10))
>>> d.sort()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/var/lib/python-support/python2.5/django/utils/datastructures.py", line 359, in complain
    raise AttributeError, self.warning
AttributeError: ImmutableList object is immutable.
>>> repr(d)
'(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)'
>>> d = ImmutableList(range(10), warning="Object is immutable!")
>>> d[1]
1
>>> d[1] = 'test'
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/var/lib/python-support/python2.5/django/utils/datastructures.py", line 359, in complain
    raise AttributeError, self.warning
AttributeError: Object is immutable!

### DictWrapper #############################################################

>>> f = lambda x: "*%s" % x
>>> d = DictWrapper({'a': 'a'}, f, 'xx_')
>>> "Normal: %(a)s. Modified: %(xx_a)s" % d
'Normal: a. Modified: *a'

"""
