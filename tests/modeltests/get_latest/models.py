"""
8. get_latest_by

Models can have a ``get_latest_by`` attribute, which should be set to the name
of a ``DateField`` or ``DateTimeField``. If ``get_latest_by`` exists, the
model's manager will get a ``latest()`` method, which will return the latest
object in the database according to that field. "Latest" means "having the date
farthest into the future."
"""

from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    expire_date = models.DateField()
    class Meta:
        get_latest_by = 'pub_date'

    def __unicode__(self):
        return self.headline

class Person(models.Model):
    name = models.CharField(max_length=30)
    birthday = models.DateField()

    # Note that this model doesn't have "get_latest_by" set.

    def __unicode__(self):
        return self.name
