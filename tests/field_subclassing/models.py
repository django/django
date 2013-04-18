"""
Tests for field subclassing.
"""

from __future__ import absolute_import

from django.db import models
from django.utils.encoding import force_text

from .fields import SmallField, SmallerField, JSONField
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class MyModel(models.Model):
    name = models.CharField(max_length=10)
    data = SmallField('small field')

    def __str__(self):
        return force_text(self.name)

class OtherModel(models.Model):
    data = SmallerField()

class DataModel(models.Model):
    data = JSONField()
