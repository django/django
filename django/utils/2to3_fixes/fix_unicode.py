"""Fixer for __unicode__ methods.

Uses the django.utils.encoding.python_2_unicode_compatible decorator.
"""

from __future__ import unicode_literals

from lib2to3 import fixer_base
from lib2to3.fixer_util import find_indentation, Name, syms, touch_import
from lib2to3.pgen2 import token
from lib2to3.pytree import Leaf, Node


class FixUnicode(fixer_base.BaseFix):

    BM_compatible = True
    PATTERN = """
    classdef< 'class' any+ ':'
              suite< any*
                     funcdef< 'def' unifunc='__unicode__'
                              parameters< '(' NAME ')' > any+ >
                     any* > >
    """

    def transform(self, node, results):
        unifunc = results["unifunc"]
        strfunc = Name("__str__", prefix=unifunc.prefix)
        unifunc.replace(strfunc)

        klass = node.clone()
        klass.prefix = '\n' + find_indentation(node)
        decorator = Node(syms.decorator, [Leaf(token.AT, "@"), Name('python_2_unicode_compatible')])
        decorated = Node(syms.decorated, [decorator, klass], prefix=node.prefix)
        node.replace(decorated)

        touch_import('django.utils.encoding', 'python_2_unicode_compatible', decorated)
