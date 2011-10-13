"""
Tests for the update() queryset method that allows in-place, multi-object
updates.
"""

from django.db import models


class DataPoint(models.Model):
    name = models.CharField(max_length=20)
    value = models.CharField(max_length=20)
    another_value = models.CharField(max_length=20, blank=True)

    def __unicode__(self):
        return unicode(self.name)

class RelatedPoint(models.Model):
    name = models.CharField(max_length=20)
    data = models.ForeignKey(DataPoint)

    def __unicode__(self):
        return unicode(self.name)


class A(models.Model):
    x = models.IntegerField(default=10)

class B(models.Model):
    a = models.ForeignKey(A)
    y = models.IntegerField(default=10)

class C(models.Model):
    y = models.IntegerField(default=10)

class D(C):
    a = models.ForeignKey(A)
