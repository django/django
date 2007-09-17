"""
Regression tests for Django built-in views
"""

from django.db import models
from django.conf import settings

class Author(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/views/authors/%s/' % self.id


class Article(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(Author)

    def __unicode__(self):
        return self.title

