"""
Tests for field subclassing.
"""
from django.db import models
from django.utils.encoding import force_text, python_2_unicode_compatible

from .fields import JSONField, Small, SmallerField, SmallField


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
