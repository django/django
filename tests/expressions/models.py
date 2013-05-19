"""
Tests for F() query expression syntax.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Employee(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)

    def __str__(self):
        return '%s %s' % (self.firstname, self.lastname)

@python_2_unicode_compatible
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

    def __str__(self):
        return self.name
