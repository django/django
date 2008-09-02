"""
Various edge-cases for model managers.
"""

from django.db import models

class OnlyFred(models.Manager):
    def get_query_set(self):
        return super(OnlyFred, self).get_query_set().filter(name='fred')

class OnlyBarney(models.Manager):
    def get_query_set(self):
        return super(OnlyBarney, self).get_query_set().filter(name='barney')

class Value42(models.Manager):
    def get_query_set(self):
        return super(Value42, self).get_query_set().filter(value=42)

class AbstractBase1(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        abstract = True

    # Custom managers
    manager1 = OnlyFred()
    manager2 = OnlyBarney()
    objects = models.Manager()

class AbstractBase2(models.Model):
    value = models.IntegerField()

    class Meta:
        abstract = True

    # Custom manager
    restricted = Value42()

# No custom manager on this class to make sure the default case doesn't break.
class AbstractBase3(models.Model):
    comment = models.CharField(max_length=50)

    class Meta:
        abstract = True

class Parent(models.Model):
    name = models.CharField(max_length=50)

    manager = OnlyFred()

    def __unicode__(self):
        return self.name

# Managers from base classes are inherited and, if no manager is specified
# *and* the parent has a manager specified, the first one (in the MRO) will
# become the default.
class Child1(AbstractBase1):
    data = models.CharField(max_length=25)

    def __unicode__(self):
        return self.data

class Child2(AbstractBase1, AbstractBase2):
    data = models.CharField(max_length=25)

    def __unicode__(self):
        return self.data

class Child3(AbstractBase1, AbstractBase3):
    data = models.CharField(max_length=25)

    def __unicode__(self):
        return self.data

class Child4(AbstractBase1):
    data = models.CharField(max_length=25)

    # Should be the default manager, although the parent managers are
    # inherited.
    default = models.Manager()

    def __unicode__(self):
        return self.data

class Child5(AbstractBase3):
    name = models.CharField(max_length=25)

    default = OnlyFred()
    objects = models.Manager()

    def __unicode__(self):
        return self.name

# Will inherit managers from AbstractBase1, but not Child4.
class Child6(Child4):
    value = models.IntegerField()

# Will not inherit default manager from parent.
class Child7(Parent):
    pass

__test__ = {"API_TESTS": """
>>> a1 = Child1.objects.create(name='fred', data='a1')
>>> a2 = Child1.objects.create(name='barney', data='a2')
>>> b1 = Child2.objects.create(name='fred', data='b1', value=1)
>>> b2 = Child2.objects.create(name='barney', data='b2', value=42)
>>> c1 = Child3.objects.create(name='fred', data='c1', comment='yes')
>>> c2 = Child3.objects.create(name='barney', data='c2', comment='no')
>>> d1 = Child4.objects.create(name='fred', data='d1')
>>> d2 = Child4.objects.create(name='barney', data='d2')
>>> e1 = Child5.objects.create(name='fred', comment='yes')
>>> e2 = Child5.objects.create(name='barney', comment='no')
>>> f1 = Child6.objects.create(name='fred', data='f1', value=42)
>>> f2 = Child6.objects.create(name='barney', data='f2', value=42)
>>> g1 = Child7.objects.create(name='fred')
>>> g2 = Child7.objects.create(name='barney')

>>> Child1.manager1.all()
[<Child1: a1>]
>>> Child1.manager2.all()
[<Child1: a2>]
>>> Child1._default_manager.all()
[<Child1: a1>]

>>> Child2._default_manager.all()
[<Child2: b1>]
>>> Child2.restricted.all()
[<Child2: b2>]

>>> Child3._default_manager.all()
[<Child3: c1>]
>>> Child3.manager1.all()
[<Child3: c1>]
>>> Child3.manager2.all()
[<Child3: c2>]

# Since Child6 inherits from Child4, the corresponding rows from f1 and f2 also
# appear here. This is the expected result.
>>> Child4._default_manager.order_by('data')
[<Child4: d1>, <Child4: d2>, <Child4: f1>, <Child4: f2>]
>>> Child4.manager1.all()
[<Child4: d1>, <Child4: f1>]

>>> Child5._default_manager.all()
[<Child5: fred>]

>>> Child6._default_manager.all()
[<Child6: f1>]

>>> Child7._default_manager.order_by('name')
[<Child7: barney>, <Child7: fred>]

"""}
