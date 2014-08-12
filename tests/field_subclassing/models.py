"""
Tests for field subclassing.
"""

import warnings

from django.db import models
from django.utils.encoding import force_text
from django.utils.deprecation import RemovedInDjango20Warning

from .fields import Small, SmallField, SmallerField, JSONField
from django.utils.encoding import python_2_unicode_compatible


# Catch warning about subfieldbase  -- remove in Django 2.0
warnings.filterwarnings(
    'ignore',
    'SubfieldBase has been deprecated. Use Field.from_db_value instead.',
    RemovedInDjango20Warning
)


@python_2_unicode_compatible
class MyModel(models.Model):
    name = models.CharField(max_length=10)
    data = SmallField('small field')

    def __str__(self):
        return force_text(self.name)


class OtherModel(models.Model):
    data = SmallerField()


class ChoicesModel(models.Model):
    SMALL_AB = Small('a', 'b')
    SMALL_CD = Small('c', 'd')
    SMALL_CHOICES = (
        (SMALL_AB, str(SMALL_AB)),
        (SMALL_CD, str(SMALL_CD)),
    )
    data = SmallField('small field', choices=SMALL_CHOICES)


class DataModel(models.Model):
    data = JSONField()
