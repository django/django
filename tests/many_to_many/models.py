"""
Many-to-many relationships

To define a many-to-many relationship, use ``ManyToManyField()``.

In this example, an ``Article`` can be published in multiple ``Publication``
objects, and a ``Publication`` has multiple ``Article`` objects.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Publication(models.Model):
    title = models.CharField(max_length=30)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ('title',)


@python_2_unicode_compatible
class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    # Assign a unicode string as name to make sure the intermediary model is
    # correctly created. Refs #20207
    publications = models.ManyToManyField(Publication, name='publications')
    tags = models.ManyToManyField(Tag, related_name='tags')

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)


# Models to test correct related_name inheritance
class AbstractArticle(models.Model):
    class Meta:
        abstract = True

    publications = models.ManyToManyField(Publication, name='publications', related_name='+')


class InheritedArticleA(AbstractArticle):
    pass


class InheritedArticleB(AbstractArticle):
    pass
