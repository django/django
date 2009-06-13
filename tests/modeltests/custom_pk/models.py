# -*- coding: utf-8 -*-
"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.
"""

from django.conf import settings
from django.db import models, transaction, IntegrityError

from fields import MyAutoField

class Employee(models.Model):
    employee_code = models.IntegerField(primary_key=True, db_column = 'code')
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    class Meta:
        ordering = ('last_name', 'first_name')

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Business(models.Model):
    name = models.CharField(max_length=20, primary_key=True)
    employees = models.ManyToManyField(Employee)
    class Meta:
        verbose_name_plural = 'businesses'

    def __unicode__(self):
        return self.name

class Bar(models.Model):
    id = MyAutoField(primary_key=True, db_index=True)

    def __unicode__(self):
        return repr(self.pk)


class Foo(models.Model):
    bar = models.ForeignKey(Bar)

__test__ = {'API_TESTS':"""
>>> dan = Employee(employee_code=123, first_name='Dan', last_name='Jones')
>>> dan.save()
>>> Employee.objects.all()
[<Employee: Dan Jones>]

>>> fran = Employee(employee_code=456, first_name='Fran', last_name='Bones')
>>> fran.save()
>>> Employee.objects.all()
[<Employee: Fran Bones>, <Employee: Dan Jones>]

>>> Employee.objects.get(pk=123)
<Employee: Dan Jones>
>>> Employee.objects.get(pk=456)
<Employee: Fran Bones>
>>> Employee.objects.get(pk=42)
Traceback (most recent call last):
    ...
DoesNotExist: Employee matching query does not exist.

# Use the name of the primary key, rather than pk.
>>> Employee.objects.get(employee_code__exact=123)
<Employee: Dan Jones>

# pk can be used as a substitute for the primary key.
>>> Employee.objects.filter(pk__in=[123, 456])
[<Employee: Fran Bones>, <Employee: Dan Jones>]

# The primary key can be accessed via the pk property on the model.
>>> e = Employee.objects.get(pk=123)
>>> e.pk
123

# Or we can use the real attribute name for the primary key:
>>> e.employee_code
123

# Fran got married and changed her last name.
>>> fran = Employee.objects.get(pk=456)
>>> fran.last_name = 'Jones'
>>> fran.save()
>>> Employee.objects.filter(last_name__exact='Jones')
[<Employee: Dan Jones>, <Employee: Fran Jones>]
>>> emps = Employee.objects.in_bulk([123, 456])
>>> emps[123]
<Employee: Dan Jones>

>>> b = Business(name='Sears')
>>> b.save()
>>> b.employees.add(dan, fran)
>>> b.employees.all()
[<Employee: Dan Jones>, <Employee: Fran Jones>]
>>> fran.business_set.all()
[<Business: Sears>]
>>> Business.objects.in_bulk(['Sears'])
{u'Sears': <Business: Sears>}

>>> Business.objects.filter(name__exact='Sears')
[<Business: Sears>]
>>> Business.objects.filter(pk='Sears')
[<Business: Sears>]

# Queries across tables, involving primary key
>>> Employee.objects.filter(business__name__exact='Sears')
[<Employee: Dan Jones>, <Employee: Fran Jones>]
>>> Employee.objects.filter(business__pk='Sears')
[<Employee: Dan Jones>, <Employee: Fran Jones>]

>>> Business.objects.filter(employees__employee_code__exact=123)
[<Business: Sears>]
>>> Business.objects.filter(employees__pk=123)
[<Business: Sears>]
>>> Business.objects.filter(employees__first_name__startswith='Fran')
[<Business: Sears>]

# Primary key may be unicode string
>>> bus = Business(name=u'jaźń')
>>> bus.save()

# The primary key must also obviously be unique, so trying to create a new
# object with the same primary key will fail.
>>> try:
...    sid = transaction.savepoint()
...    Employee.objects.create(employee_code=123, first_name='Fred', last_name='Jones')
...    transaction.savepoint_commit(sid)
... except Exception, e:
...    if isinstance(e, IntegrityError):
...        transaction.savepoint_rollback(sid)
...        print "Pass"
...    else:
...        print "Fail with %s" % type(e)
Pass

# Regression for #10785 -- Custom fields can be used for primary keys.
>>> new_bar = Bar.objects.create()
>>> new_foo = Foo.objects.create(bar=new_bar)
>>> f = Foo.objects.get(bar=new_bar.pk)
>>> f == new_foo
True
>>> f.bar == new_bar
True

>>> f = Foo.objects.get(bar=new_bar)
>>> f == new_foo
True
>>> f.bar == new_bar
True

"""}

# SQLite lets objects be saved with an empty primary key, even though an
# integer is expected. So we can't check for an error being raised in that case
# for SQLite. Remove it from the suite for this next bit.
if settings.DATABASE_ENGINE != 'sqlite3':
    __test__["API_TESTS"] += """
# The primary key must be specified, so an error is raised if you try to create
# an object without it.
>>> try:
...     sid = transaction.savepoint()
...     Employee.objects.create(first_name='Tom', last_name='Smith')
...     print 'hello'
...     transaction.savepoint_commit(sid)
...     print 'hello2'
... except Exception, e:
...     if isinstance(e, IntegrityError):
...         transaction.savepoint_rollback(sid)
...         print "Pass"
...     else:
...         print "Fail with %s" % type(e)
Pass

"""
