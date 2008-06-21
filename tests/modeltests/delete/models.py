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


__test__ = {'API_TESTS': """
# Due to the way that transactions work in the test harness,
# doing m.delete() here can work but fail in a real situation,
# since it may delete all objects, but not in the right order.
# So we manually check that the order of deletion is correct.

# Also, it is possible that the order is correct 'accidentally', due
# solely to order of imports etc.  To check this, we set the order
# that 'get_models()' will retrieve to a known 'tricky' order, and
# then try again with the reverse and try again.  Slightly naughty
# access to internals here.

>>> from django.utils.datastructures import SortedDict
>>> from django.db.models.loading import cache

# Nice order
>>> cache.app_models['delete'].keyOrder = ['a', 'b', 'c', 'd']
>>> del A._meta._related_objects_cache
>>> del B._meta._related_objects_cache
>>> del C._meta._related_objects_cache
>>> del D._meta._related_objects_cache



>>> a1 = A()
>>> a1.save()
>>> b1 = B(a=a1)
>>> b1.save()
>>> c1 = C(b=b1)
>>> c1.save()
>>> d1 = D(c=c1, a=a1)
>>> d1.save()

>>> sd = SortedDict()
>>> a1._collect_sub_objects(sd)
>>> list(reversed(sd.keys()))
[<class 'modeltests.delete.models.D'>, <class 'modeltests.delete.models.C'>, <class 'modeltests.delete.models.B'>, <class 'modeltests.delete.models.A'>]
>>> a1.delete()

# Same again with a known bad order
>>> cache.app_models['delete'].keyOrder = ['d', 'c', 'b', 'a']
>>> del A._meta._related_objects_cache
>>> del B._meta._related_objects_cache
>>> del C._meta._related_objects_cache
>>> del D._meta._related_objects_cache


>>> a2 = A()
>>> a2.save()
>>> b2 = B(a=a2)
>>> b2.save()
>>> c2 = C(b=b2)
>>> c2.save()
>>> d2 = D(c=c2, a=a2)
>>> d2.save()

>>> sd2 = SortedDict()
>>> a2._collect_sub_objects(sd2)
>>> list(reversed(sd2.keys()))
[<class 'modeltests.delete.models.D'>, <class 'modeltests.delete.models.C'>, <class 'modeltests.delete.models.B'>, <class 'modeltests.delete.models.A'>]
>>> a2.delete()



"""
}
