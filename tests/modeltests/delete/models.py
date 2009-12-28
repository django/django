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


__test__ = {'API_TESTS': """
### Tests for models A,B,C,D ###

## First, test the CollectedObjects data structure directly

>>> from django.db.models.query import CollectedObjects

>>> g = CollectedObjects()
>>> g.add("key1", 1, "item1", None)
False
>>> g["key1"]
{1: 'item1'}
>>> g.add("key2", 1, "item1", "key1")
False
>>> g.add("key2", 2, "item2", "key1")
False
>>> g["key2"]
{1: 'item1', 2: 'item2'}
>>> g.add("key3", 1, "item1", "key1")
False
>>> g.add("key3", 1, "item1", "key2")
True
>>> g.ordered_keys()
['key3', 'key2', 'key1']

>>> g.add("key2", 1, "item1", "key3")
True
>>> g.ordered_keys()
Traceback (most recent call last):
    ...
CyclicDependency: There is a cyclic dependency of items to be processed.


## Second, test the usage of CollectedObjects by Model.delete()

# Due to the way that transactions work in the test harness,
# doing m.delete() here can work but fail in a real situation,
# since it may delete all objects, but not in the right order.
# So we manually check that the order of deletion is correct.

# Also, it is possible that the order is correct 'accidentally', due
# solely to order of imports etc.  To check this, we set the order
# that 'get_models()' will retrieve to a known 'nice' order, and
# then try again with a known 'tricky' order.  Slightly naughty
# access to internals here :-)

# If implementation changes, then the tests may need to be simplified:
#  - remove the lines that set the .keyOrder and clear the related
#    object caches
#  - remove the second set of tests (with a2, b2 etc)

>>> from django.db.models.loading import cache

>>> def clear_rel_obj_caches(models):
...     for m in models:
...         if hasattr(m._meta, '_related_objects_cache'):
...             del m._meta._related_objects_cache

# Nice order
>>> cache.app_models['delete'].keyOrder = ['a', 'b', 'c', 'd']
>>> clear_rel_obj_caches([A, B, C, D])

>>> a1 = A()
>>> a1.save()
>>> b1 = B(a=a1)
>>> b1.save()
>>> c1 = C(b=b1)
>>> c1.save()
>>> d1 = D(c=c1, a=a1)
>>> d1.save()

>>> o = CollectedObjects()
>>> a1._collect_sub_objects(o)
>>> o.keys()
[<class 'modeltests.delete.models.D'>, <class 'modeltests.delete.models.C'>, <class 'modeltests.delete.models.B'>, <class 'modeltests.delete.models.A'>]
>>> a1.delete()

# Same again with a known bad order
>>> cache.app_models['delete'].keyOrder = ['d', 'c', 'b', 'a']
>>> clear_rel_obj_caches([A, B, C, D])

>>> a2 = A()
>>> a2.save()
>>> b2 = B(a=a2)
>>> b2.save()
>>> c2 = C(b=b2)
>>> c2.save()
>>> d2 = D(c=c2, a=a2)
>>> d2.save()

>>> o = CollectedObjects()
>>> a2._collect_sub_objects(o)
>>> o.keys()
[<class 'modeltests.delete.models.D'>, <class 'modeltests.delete.models.C'>, <class 'modeltests.delete.models.B'>, <class 'modeltests.delete.models.A'>]
>>> a2.delete()

### Tests for models E,F - nullable related fields ###

## First, test the CollectedObjects data structure directly

>>> g = CollectedObjects()
>>> g.add("key1", 1, "item1", None)
False
>>> g.add("key2", 1, "item1", "key1", nullable=True)
False
>>> g.add("key1", 1, "item1", "key2")
True
>>> g.ordered_keys()
['key1', 'key2']

## Second, test the usage of CollectedObjects by Model.delete()

>>> e1 = E()
>>> e1.save()
>>> f1 = F(e=e1)
>>> f1.save()
>>> e1.f = f1
>>> e1.save()

# Since E.f is nullable, we should delete F first (after nulling out
# the E.f field), then E.

>>> o = CollectedObjects()
>>> e1._collect_sub_objects(o)
>>> o.keys()
[<class 'modeltests.delete.models.F'>, <class 'modeltests.delete.models.E'>]

# temporarily replace the UpdateQuery class to verify that E.f is actually nulled out first
>>> import django.db.models.sql
>>> class LoggingUpdateQuery(django.db.models.sql.UpdateQuery):
...     def clear_related(self, related_field, pk_list, using):
...         print "CLEARING FIELD",related_field.name
...         return super(LoggingUpdateQuery, self).clear_related(related_field, pk_list, using)
>>> original_class = django.db.models.sql.UpdateQuery
>>> django.db.models.sql.UpdateQuery = LoggingUpdateQuery
>>> e1.delete()
CLEARING FIELD f

>>> e2 = E()
>>> e2.save()
>>> f2 = F(e=e2)
>>> f2.save()
>>> e2.f = f2
>>> e2.save()

# Same deal as before, though we are starting from the other object.

>>> o = CollectedObjects()
>>> f2._collect_sub_objects(o)
>>> o.keys()
[<class 'modeltests.delete.models.F'>, <class 'modeltests.delete.models.E'>]

>>> f2.delete()
CLEARING FIELD f

# Put this back to normal
>>> django.db.models.sql.UpdateQuery = original_class
"""
}
