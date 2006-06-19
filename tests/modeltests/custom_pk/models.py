"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.
"""

from django.db import models

class Employee(models.Model):
    employee_code = models.CharField(maxlength=10, primary_key=True,
            db_column = 'code')
    first_name = models.CharField(maxlength=20)
    last_name = models.CharField(maxlength=20)
    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Business(models.Model):
    name = models.CharField(maxlength=20, primary_key=True)
    employees = models.ManyToManyField(Employee)
    class Meta:
        verbose_name_plural = 'businesses'

    def __str__(self):
        return self.name

API_TESTS = """
>>> dan = Employee(employee_code='ABC123', first_name='Dan', last_name='Jones')
>>> dan.save()
>>> Employee.objects.all()
[<Employee: Dan Jones>]

>>> fran = Employee(employee_code='XYZ456', first_name='Fran', last_name='Bones')
>>> fran.save()
>>> Employee.objects.all()
[<Employee: Fran Bones>, <Employee: Dan Jones>]

>>> Employee.objects.get(pk='ABC123')
<Employee: Dan Jones>
>>> Employee.objects.get(pk='XYZ456')
<Employee: Fran Bones>
>>> Employee.objects.get(pk='foo')
Traceback (most recent call last):
    ...
DoesNotExist: Employee matching query does not exist.

# Use the name of the primary key, rather than pk.
>>> Employee.objects.get(employee_code__exact='ABC123')
<Employee: Dan Jones>

# Fran got married and changed her last name.
>>> fran = Employee.objects.get(pk='XYZ456')
>>> fran.last_name = 'Jones'
>>> fran.save()
>>> Employee.objects.filter(last_name__exact='Jones')
[<Employee: Dan Jones>, <Employee: Fran Jones>]
>>> Employee.objects.in_bulk(['ABC123', 'XYZ456'])
{'XYZ456': <Employee: Fran Jones>, 'ABC123': <Employee: Dan Jones>}

>>> b = Business(name='Sears')
>>> b.save()
>>> b.employees.add(dan, fran)
>>> b.employees.all()
[<Employee: Dan Jones>, <Employee: Fran Jones>]
>>> fran.business_set.all()
[<Business: Sears>]
>>> Business.objects.in_bulk(['Sears'])
{'Sears': <Business: Sears>}

>>> Business.objects.filter(name__exact='Sears')
[<Business: Sears>]
>>> Business.objects.filter(pk='Sears')
[<Business: Sears>]

# Queries across tables, involving primary key
>>> Employee.objects.filter(business__name__exact='Sears')
[<Employee: Dan Jones>, <Employee: Fran Jones>]
>>> Employee.objects.filter(business__pk='Sears')
[<Employee: Dan Jones>, <Employee: Fran Jones>]

>>> Business.objects.filter(employees__employee_code__exact='ABC123')
[<Business: Sears>]
>>> Business.objects.filter(employees__pk='ABC123')
[<Business: Sears>]
>>> Business.objects.filter(employees__first_name__startswith='Fran')
[<Business: Sears>]

"""
