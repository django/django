# -*- coding: utf-8 -*-

r"""
>>> words(7)
u'lorem ipsum dolor sit amet consectetur adipisicing'

>>> paragraphs(1)
['Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.']

>>> from django.template import loader, Context
>>> t = loader.get_template_from_string("{% load webdesign %}{% lorem 3 w %}")
>>> t.render(Context({}))
u'lorem ipsum dolor'
"""

from django.contrib.webdesign.lorem_ipsum import *

if __name__ == '__main__':
    import doctest
    doctest.testmod()
