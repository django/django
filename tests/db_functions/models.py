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
    age = models.PositiveSmallIntegerField(default=30)

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
    updated = models.DateTimeField(null=True, blank=True)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class Fan(models.Model):
    name = models.CharField(max_length=50)
    age = models.PositiveSmallIntegerField(default=30)
    author = models.ForeignKey(Author, models.CASCADE, related_name='fans')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class DTModel(models.Model):
    name = models.CharField(max_length=32)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return 'DTModel({0})'.format(self.name)


class DecimalModel(models.Model):
    n1 = models.DecimalField(decimal_places=2, max_digits=6)
    n2 = models.DecimalField(decimal_places=2, max_digits=6)
