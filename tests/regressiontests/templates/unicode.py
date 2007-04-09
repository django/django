# -*- coding: utf-8 -*-

unicode_tests = ur"""
Templates can be created from unicode strings.
>>> from django.template import *
>>> t1 = Template(u'ŠĐĆŽćžšđ {{ var }}')

Templates can also be created from bytestrings. These are assumed by encoded using UTF-8.
>>> s = '\xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91 {{ var }}'
>>> t2 = Template(s)
>>> s = '\x80\xc5\xc0'
>>> Template(s)
Traceback (most recent call last):
    ...
TemplateEncodingError: Templates can only be constructed from unicode or UTF-8 strings.

Contexts can be constructed from unicode or UTF-8 bytestrings.
>>> c1 = Context({'var': 'foo'})
>>> c2 = Context({u'var': 'foo'})
>>> c3 = Context({'var': u'Đđ'})
>>> c4 = Context({u'var': '\xc4\x90\xc4\x91'})

Since both templates and all four contexts represent the same thing, they all
render the same (and are returned as bytestrings).
>>> t1.render(c3) == t2.render(c3)
True
>>> type(t1.render(c3))
<type 'str'>
"""
# -*- coding: utf-8 -*-

unicode_tests = ur"""
Templates can be created from unicode strings.
>>> from django.template import *
>>> t1 = Template(u'ŠĐĆŽćžšđ {{ var }}')

Templates can also be created from bytestrings. These are assumed by encoded using UTF-8.
>>> s = '\xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91 {{ var }}'
>>> t2 = Template(s)
>>> s = '\x80\xc5\xc0'
>>> Template(s)
Traceback (most recent call last):
    ...
TemplateEncodingError: Templates can only be constructed from unicode or UTF-8 strings.

Contexts can be constructed from unicode or UTF-8 bytestrings.
>>> c1 = Context({'var': 'foo'})
>>> c2 = Context({u'var': 'foo'})
>>> c3 = Context({'var': u'Đđ'})
>>> c4 = Context({u'var': '\xc4\x90\xc4\x91'})

Since both templates and all four contexts represent the same thing, they all
render the same (and are returned as bytestrings).
>>> t1.render(c3) == t2.render(c3)
True
>>> type(t1.render(c3))
<type 'str'>
"""
