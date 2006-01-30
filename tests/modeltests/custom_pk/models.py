"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.
"""

from django.db import models

class Employee(models.Model):
    employee_code = models.CharField(maxlength=10, primary_key=True)
    first_name = models.CharField(maxlength=20)
    last_name = models.CharField(maxlength=20)
    class Meta:
        ordering = ('last_name', 'first_name')

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Business(models.Model):
    name = models.CharField(maxlength=20, primary_key=True)
    employees = models.ManyToManyField(Employee)
    class Meta:
        verbose_name_plural = 'businesses'

    def __repr__(self):
        return self.name

API_TESTS = """
>>> dan = Employee(employee_code='ABC123', first_name='Dan', last_name='Jones')
>>> dan.save()
>>> list(Employee.objects.all())
[Dan Jones]

>>> fran = Employee(employee_code='XYZ456', first_name='Fran', last_name='Bones')
>>> fran.save()
>>> list(Employee.objects.all())
[Fran Bones, Dan Jones]

>>> Employee.objects.get(pk='ABC123')
Dan Jones
>>> Employee.objects.get(pk='XYZ456')
Fran Bones
>>> Employee.objects.get(pk='foo')
Traceback (most recent call last):
    ...
DoesNotExist: Employee does not exist for {'pk': 'foo'}

# Use the name of the primary key, rather than pk.
>>> Employee.objects.get(employee_code__exact='ABC123')
Dan Jones

# Fran got married and changed her last name.
>>> fran = Employee.objects.get(pk='XYZ456')
>>> fran.last_name = 'Jones'
>>> fran.save()
>>> list(Employee.objects.filter(last_name__exact='Jones'))
[Dan Jones, Fran Jones]
>>> Employee.objects.in_bulk(['ABC123', 'XYZ456'])
{'XYZ456': Fran Jones, 'ABC123': Dan Jones}

>>> b = Business(name='Sears')
>>> b.save()
>>> b.set_employees([dan.employee_code, fran.employee_code])
True
>>> list(b.employee_set)
[Dan Jones, Fran Jones]
>>> list(fran.business_set)
[Sears]
>>> Business.objects.in_bulk(['Sears'])
{'Sears': Sears}

>>> list(Business.objects.filter(name__exact='Sears'))
[Sears]
>>> list(Business.objects.filter(pk='Sears'))
[Sears]

# Queries across tables, involving primary key
>>> list(Employee.objects.filter(business__name__exact='Sears'))
[Dan Jones, Fran Jones]
>>> list(Employee.objects.filter(business__pk='Sears'))
[Dan Jones, Fran Jones]

>>> list(Business.objects.filter(employees__employee_code__exact='ABC123'))
[Sears]
>>> list(Business.objects.filter(employees__pk='ABC123'))
[Sears]
>>> list(Business.objects.filter(employees__first_name__startswith='Fran'))
[Sears]

"""
