"""
Tests for the update() queryset method that allows in-place, multi-object
updates.
"""

from django.db import models


class DataPoint(models.Model):
    name = models.CharField(max_length=20)
    value = models.CharField(max_length=20)
    another_value = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name


class RelatedPoint(models.Model):
    name = models.CharField(max_length=20)
    data = models.ForeignKey(DataPoint, models.CASCADE)

    def __str__(self):
        return self.name


class A(models.Model):
    x = models.IntegerField(default=10)


class B(models.Model):
    a = models.ForeignKey(A, models.CASCADE)
    y = models.IntegerField(default=10)


class C(models.Model):
    y = models.IntegerField(default=10)


class D(C):
    a = models.ForeignKey(A, models.CASCADE)



class Employee(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    salary = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return '%s %s' % (self.firstname, self.lastname)


class Company(models.Model):
    name = models.CharField(max_length=100)
    num_employees = models.PositiveIntegerField()
    num_chairs = models.PositiveIntegerField()
    ceo = models.ForeignKey(
        Employee,
        models.CASCADE,
        related_name='company_ceo_set',
    )
    point_of_contact = models.ForeignKey(
        Employee,
        models.SET_NULL,
        related_name='company_point_of_contact_set',
        null=True,
    )
    based_in_eu = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Foo(models.Model):
    target = models.CharField(max_length=10, unique=True)


class Bar(models.Model):
    foo = models.ForeignKey(Foo, models.CASCADE, to_field='target')
    m2m_foo = models.ManyToManyField(Foo, related_name='m2m_foo')
