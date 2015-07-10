# -*- coding: utf-8 -*-
"""
Using a custom primary key

By default, Django adds an ``"id"`` field to each model. But you can override
this behavior by explicitly adding ``primary_key=True`` to a field.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from .fields import MyAutoField


@python_2_unicode_compatible
class Employee(models.Model):
    employee_code = models.IntegerField(primary_key=True, db_column='code')
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


@python_2_unicode_compatible
class Business(models.Model):
    name = models.CharField(max_length=20, primary_key=True)
    employees = models.ManyToManyField(Employee)

    class Meta:
        verbose_name_plural = 'businesses'

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Bar(models.Model):
    id = MyAutoField(primary_key=True, db_index=True)

    def __str__(self):
        return repr(self.pk)


class Foo(models.Model):
    bar = models.ForeignKey(Bar)
