"""
33. get_or_create()

``get_or_create()`` does what it says: it tries to look up an object with the
given parameters. If an object isn't found, it creates one with the given
parameters.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Person(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birthday = models.DateField()

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

class ManualPrimaryKeyTest(models.Model):
    id = models.IntegerField(primary_key=True)
    data = models.CharField(max_length=100)
