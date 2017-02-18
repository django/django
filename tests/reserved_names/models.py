"""
Using SQL reserved names

Need to use a reserved SQL name as a column name or table name? Need to include
a hyphen in a column or table name? No problem. Django quotes names
appropriately behind the scenes, so your database won't complain about
reserved-name usage.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Thing(models.Model):
    when = models.CharField(max_length=1, primary_key=True)
    join = models.CharField(max_length=1)
    like = models.CharField(max_length=1)
    drop = models.CharField(max_length=1)
    alter = models.CharField(max_length=1)
    having = models.CharField(max_length=1)
    where = models.DateField(max_length=1)
    has_hyphen = models.CharField(max_length=1, db_column='has-hyphen')

    class Meta:
        db_table = 'select'

    def __str__(self):
        return self.when
