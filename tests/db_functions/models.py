"""
Tests for built in Function expressions.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=50)
    alias = models.CharField(max_length=50, null=True, blank=True)
    goes_by = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Article(models.Model):
    authors = models.ManyToManyField(Author, related_name='articles')
    title = models.CharField(max_length=50)
    summary = models.CharField(max_length=200, null=True, blank=True)
    text = models.TextField()
    written = models.DateTimeField()
    published = models.DateTimeField(null=True, blank=True)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title
