"""
Tests for F() query expression syntax.
"""

from django.db import models

class Employee(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)

    def __unicode__(self):
        return u'%s %s' % (self.firstname, self.lastname)

class Company(models.Model):
    name = models.CharField(max_length=100)
    num_employees = models.PositiveIntegerField()
    num_chairs = models.PositiveIntegerField()
    ceo = models.ForeignKey(
        Employee,
        related_name='company_ceo_set')
    point_of_contact = models.ForeignKey(
        Employee,
        related_name='company_point_of_contact_set',
        null=True)

    def __unicode__(self):
        return self.name


__test__ = {'API_TESTS': """
>>> from django.db.models import F

>>> Company(name='Example Inc.', num_employees=2300, num_chairs=5,
...     ceo=Employee.objects.create(firstname='Joe', lastname='Smith')).save()
>>> Company(name='Foobar Ltd.', num_employees=3, num_chairs=3,
...     ceo=Employee.objects.create(firstname='Frank', lastname='Meyer')).save()
>>> Company(name='Test GmbH', num_employees=32, num_chairs=1,
...     ceo=Employee.objects.create(firstname='Max', lastname='Mustermann')).save()

# We can filter for companies where the number of employees is greater than the
# number of chairs.

>>> Company.objects.filter(num_employees__gt=F('num_chairs'))
[<Company: Example Inc.>, <Company: Test GmbH>]

# The relation of a foreign key can become copied over to an other foreign key.

>>> Company.objects.update(point_of_contact=F('ceo'))
3

>>> [c.point_of_contact for c in Company.objects.all()]
[<Employee: Joe Smith>, <Employee: Frank Meyer>, <Employee: Max Mustermann>]

>>> c = Company.objects.all()[0]
>>> c.point_of_contact = Employee.objects.create(firstname="Guido", lastname="van Rossum")
>>> c.save()

# F Expressions can also span joins
>>> Company.objects.filter(ceo__firstname=F('point_of_contact__firstname')).distinct()
[<Company: Foobar Ltd.>, <Company: Test GmbH>]

>>> _ = Company.objects.exclude(ceo__firstname=F('point_of_contact__firstname')).update(name='foo')
>>> Company.objects.exclude(ceo__firstname=F('point_of_contact__firstname')).get().name
u'foo'

>>> _ = Company.objects.exclude(ceo__firstname=F('point_of_contact__firstname')).update(name=F('point_of_contact__lastname'))
Traceback (most recent call last):
...
FieldError: Joined field references are not permitted in this query

"""}
