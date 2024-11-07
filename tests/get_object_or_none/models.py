"""
DB-API Shortcuts

``get_object_or_none()`` is a shortcut function to be used in view functions for
performing a ``get()`` lookup and returning ``None`` if a ``DoesNotExist``
exception was raised during the ``get()`` call.
"""

from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=50)


class ArticleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(authors__name__icontains="sir")


class AttributeErrorManager(models.Manager):
    def get_queryset(self):
        raise AttributeError("AttributeErrorManager")


class Article(models.Model):
    authors = models.ManyToManyField(Author)
    title = models.CharField(max_length=50)
    objects = models.Manager()
    by_a_sir = ArticleManager()
    attribute_error_objects = AttributeErrorManager()
