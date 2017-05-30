"""
Tests for F() query expression syntax.
"""
from __future__ import unicode_literals

import uuid

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Employee(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    salary = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return '%s %s' % (self.firstname, self.lastname)


@python_2_unicode_compatible
class Company(models.Model):
    name = models.CharField(max_length=100)
    num_employees = models.PositiveIntegerField()
    num_chairs = models.PositiveIntegerField()
    ceo = models.ForeignKey(
        Employee,
        models.CASCADE,
        related_name='company_ceo_set')
    point_of_contact = models.ForeignKey(
        Employee,
        models.SET_NULL,
        related_name='company_point_of_contact_set',
        null=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Number(models.Model):
    integer = models.BigIntegerField(db_column='the_integer')
    float = models.FloatField(null=True, db_column='the_float')

    def __str__(self):
        return '%i, %.3f' % (self.integer, self.float)


class Experiment(models.Model):
    name = models.CharField(max_length=24)
    assigned = models.DateField()
    completed = models.DateField()
    estimated_time = models.DurationField()
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ('name',)

    def duration(self):
        return self.end - self.start


@python_2_unicode_compatible
class Result(models.Model):
    experiment = models.ForeignKey(Experiment, models.CASCADE)
    result_time = models.DateTimeField()

    def __str__(self):
        return "Result at %s" % self.result_time


@python_2_unicode_compatible
class Time(models.Model):
    time = models.TimeField(null=True)

    def __str__(self):
        return "%s" % self.time


@python_2_unicode_compatible
class SimulationRun(models.Model):
    start = models.ForeignKey(Time, models.CASCADE, null=True, related_name='+')
    end = models.ForeignKey(Time, models.CASCADE, null=True, related_name='+')
    midpoint = models.TimeField()

    def __str__(self):
        return "%s (%s to %s)" % (self.midpoint, self.start, self.end)


class UUIDPK(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)


@python_2_unicode_compatible
class UUID(models.Model):
    uuid = models.UUIDField(null=True)
    uuid_fk = models.ForeignKey(UUIDPK, models.CASCADE, null=True)

    def __str__(self):
        return "%s" % self.uuid
