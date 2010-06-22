# coding: utf-8
"""
Tests for some corner cases with deleting.
"""

from django.db import models

class DefaultRepr(object):
    def __repr__(self):
        return u"<%s: %s>" % (self.__class__.__name__, self.__dict__)

class A(DefaultRepr, models.Model):
    pass

class B(DefaultRepr, models.Model):
    a = models.ForeignKey(A)

class C(DefaultRepr, models.Model):
    b = models.ForeignKey(B)

class D(DefaultRepr, models.Model):
    c = models.ForeignKey(C)
    a = models.ForeignKey(A)

# Simplified, we have:
# A
# B -> A
# C -> B
# D -> C
# D -> A

# So, we must delete Ds first of all, then Cs then Bs then As.
# However, if we start at As, we might find Bs first (in which
# case things will be nice), or find Ds first.

# Some mutually dependent models, but nullable
class E(DefaultRepr, models.Model):
    f = models.ForeignKey('F', null=True, related_name='e_rel')

class F(DefaultRepr, models.Model):
    e = models.ForeignKey(E, related_name='f_rel')

