# -*- coding: utf-8 -*-
"""
14. Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.
"""

from __future__ import absolute_import

from django.db import models

from .fields import MyAutoField


class Employee(models.Model):
    employee_code = models.IntegerField(primary_key=True, db_column = 'code')
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    class Meta:
        ordering = ('last_name', 'first_name')

    def __unicode__(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Business(models.Model):
    name = models.CharField(max_length=20, primary_key=True)
    employees = models.ManyToManyField(Employee)
    class Meta:
        verbose_name_plural = 'businesses'

    def __unicode__(self):
        return self.name

class Bar(models.Model):
    id = MyAutoField(primary_key=True, db_index=True)

    def __unicode__(self):
        return repr(self.pk)


class Foo(models.Model):
    bar = models.ForeignKey(Bar)

