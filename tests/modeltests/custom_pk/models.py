"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.
"""

from django.core import meta

class Employee(meta.Model):
    employee_code = meta.CharField(maxlength=10, primary_key=True)
    first_name = meta.CharField(maxlength=20)
    last_name = meta.CharField(maxlength=20)
    class META:
        ordering = ('last_name', 'first_name')

    def __repr__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Business(meta.Model):
    name = meta.CharField(maxlength=20, primary_key=True)
    employees = meta.ManyToManyField(Employee)
    class META:
        verbose_name_plural = 'businesses'
        module_name = 'businesses'

    def __repr__(self):
        return self.name

API_TESTS = """
>>> dan = Employee(employee_code='ABC123', first_name='Dan', last_name='Jones')
>>> dan.save()
>>> Employee.objects.get_list()
[Dan Jones]

>>> fran = Employee(employee_code='XYZ456', first_name='Fran', last_name='Bones')
>>> fran.save()
>>> Employee.objects.get_list()
[Fran Bones, Dan Jones]

>>> Employee.objects.get_object(pk='ABC123')
Dan Jones
>>> Employee.objects.get_object(pk='XYZ456')
Fran Bones
>>> Employee.objects.get_object(pk='foo')
Traceback (most recent call last):
    ...
EmployeeDoesNotExist: Employee does not exist for {'pk': 'foo'}

# Fran got married and changed her last name.
>>> fran = Employee.objects.get_object(pk='XYZ456')
>>> fran.last_name = 'Jones'
>>> fran.save()
>>> Employee.objects.get_list(last_name__exact='Jones')
[Dan Jones, Fran Jones]
>>> Employee.objects.get_in_bulk(['ABC123', 'XYZ456'])
{'XYZ456': Fran Jones, 'ABC123': Dan Jones}

>>> b = Business(name='Sears')
>>> b.save()
>>> b.set_employees([dan.employee_code, fran.employee_code])
True
>>> b.get_employee_list()
[Dan Jones, Fran Jones]
>>> fran.get_business_list()
[Sears]
>>> Business.objects.get_in_bulk(['Sears'])
{'Sears': Sears}
"""
