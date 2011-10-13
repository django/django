"""
Model for testing arithmetic expressions.
"""
from django.db import models


class Number(models.Model):
    integer = models.IntegerField(db_column='the_integer')
    float = models.FloatField(null=True, db_column='the_float')

    def __unicode__(self):
        return u'%i, %.3f' % (self.integer, self.float)

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

