"""
35. DB-API Shortcuts

``get_object_or_404()`` is a shortcut function to be used in view functions for
performing a ``get()`` lookup and raising a ``Http404`` exception if a
``DoesNotExist`` exception was raised during the ``get()`` call.

``get_list_or_404()`` is a shortcut function to be used in view functions for
performing a ``filter()`` lookup and raising a ``Http404`` exception if a
``DoesNotExist`` exception was raised during the ``filter()`` call.
"""

from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404, get_list_or_404

class Author(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

class ArticleManager(models.Manager):
    def get_query_set(self):
        return super(ArticleManager, self).get_query_set().filter(authors__name__icontains='sir')

class Article(models.Model):
    authors = models.ManyToManyField(Author)
    title = models.CharField(max_length=50)
    objects = models.Manager()
    by_a_sir = ArticleManager()

    def __unicode__(self):
        return self.title
