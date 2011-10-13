# coding: utf-8
"""
32. Callable defaults

You can pass callable objects as the ``default`` parameter to a field. When
the object is created without an explicit value passed in, Django will call
the method to determine the default value.

This example uses ``datetime.datetime.now`` as the default for the ``pub_date``
field.
"""

from datetime import datetime

from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField(default=datetime.now)

    def __unicode__(self):
        return self.headline
