"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.

NOTE: This isn't yet supported. This model exists as a unit test that currently
fails.
"""

from django.core import meta

class Employee(meta.Model):
    fields = (
        meta.CharField('employee_code', maxlength=10, primary_key=True),
        meta.CharField('first_name', maxlength=20),
        meta.CharField('last_name', maxlength=20),
    )
    ordering = ('last_name', 'first_name')

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

API_TESTS = """
>>> dan = employees.Employee(employee_code='ABC123', first_name='Dan', last_name='Jones')
>>> dan.save()
>>> employees.get_list()
[Dan Jones]

>>> fran = employees.Employee(employee_code='XYZ456', first_name='Fran', last_name='Bones')
>>> fran.save()
>>> employees.get_list()
[Fran Bones, Dan Jones]

>>> employees.get_object(pk='ABC123')
Dan Jones
>>> employees.get_object(pk='XYZ456')
Fran Bones
>>> employees.get_object(pk='foo')
Traceback (most recent call last):
    ...
EmployeeDoesNotExist: Employee does not exist for {'pk': 'foo'}

# Fran got married and changed her last name.
>>> fran = employees.get_object(pk='XYZ456')
>>> fran.last_name = 'Jones'
>>> fran.save()
>>> employees.get_list(last_name__exact='Jones')
[Dan Jones, Fran Jones]
"""
