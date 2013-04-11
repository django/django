"""
20. Multiple many-to-many relationships between the same two tables

In this example, an ``Article`` can have many "primary" ``Category`` objects
and many "secondary" ``Category`` objects.

Set ``related_name`` to designate what the reverse relationship is called.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(max_length=20)
    class Meta:
       ordering = ('name',)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()
    primary_categories = models.ManyToManyField(Category, related_name='primary_article_set')
    secondary_categories = models.ManyToManyField(Category, related_name='secondary_article_set')
    class Meta:
       ordering = ('pub_date',)

    def __str__(self):
        return self.headline

