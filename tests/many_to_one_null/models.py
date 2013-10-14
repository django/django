"""
16. Many-to-one relationships that can be null

To define a many-to-one relationship that can have a null foreign key, use
``ForeignKey()`` with ``null=True`` .
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Reporter(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    reporter = models.ForeignKey(Reporter, null=True)

    class Meta:
        ordering = ('headline',)

    def __str__(self):
        return self.headline
