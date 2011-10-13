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
