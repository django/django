# coding: utf-8

context_tests = r"""
>>> from django.template import Context
>>> c = Context({'a': 1, 'b': 'xyzzy'})
>>> c['a']
1
>>> c.push()
{}
>>> c['a'] = 2
>>> c['a']
2
>>> c.get('a')
2
>>> c.pop()
{'a': 2}
>>> c['a']
1
>>> c.get('foo', 42)
42
"""

