"""
Model for testing arithmetic expressions.
"""
from django.db import models

class Number(models.Model):
    integer = models.IntegerField(db_column='the_integer')
    float = models.FloatField(null=True, db_column='the_float')

    def __unicode__(self):
        return u'%i, %.3f' % (self.integer, self.float)

