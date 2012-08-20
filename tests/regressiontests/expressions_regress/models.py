from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
"""
Model for testing arithmetic expressions.
"""
from django.db import models


@python_2_unicode_compatible
class Number(models.Model):
    integer = models.IntegerField(db_column='the_integer')
    float = models.FloatField(null=True, db_column='the_float')

    def __str__(self):
        return '%i, %.3f' % (self.integer, self.float)

class Experiment(models.Model):
    name = models.CharField(max_length=24)
    assigned = models.DateField()
    completed = models.DateField()
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ('name',)

    def duration(self):
        return self.end - self.start

