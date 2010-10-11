"""
6. Specifying ordering

Specify default ordering for a model using the ``ordering`` attribute, which
should be a list or tuple of field names. This tells Django how to order
``QuerySet`` results.

If a field name in ``ordering`` starts with a hyphen, that field will be
ordered in descending order. Otherwise, it'll be ordered in ascending order.
The special-case field name ``"?"`` specifies random order.

The ordering attribute is not required. If you leave it off, ordering will be
undefined -- not random, just undefined.
"""

from django.db import models


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __unicode__(self):
        return self.headline
