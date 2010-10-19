"""
5. Many-to-many relationships

To define a many-to-many relationship, use ``ManyToManyField()``.

In this example, an ``Article`` can be published in multiple ``Publication``
objects, and a ``Publication`` has multiple ``Article`` objects.
"""

from django.db import models

class Publication(models.Model):
    title = models.CharField(max_length=30)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)

class Article(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(Publication)

    def __unicode__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)
