"""
# Tests for stuff in django.utils.text.

>>> from django.utils.text import *

### smart_split ###########################################################
>>> list(smart_split(r'''This is "a person" test.'''))
[u'This', u'is', u'"a person"', u'test.']
>>> print list(smart_split(r'''This is "a person's" test.'''))[2]
"a person's"
>>> print list(smart_split(r'''This is "a person\\"s" test.'''))[2]
"a person"s"
>>> list(smart_split('''"a 'one'''))
[u'"a', u"'one"]
>>> print list(smart_split(r'''all friends' tests'''))[1]
friends'
"""
