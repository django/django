"""
Testing signals before/after saving and deleting.
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Person(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


@python_2_unicode_compatible
class Car(models.Model):
    make = models.CharField(max_length=20)
    model = models.CharField(max_length=20)

    def __str__(self):
        return "%s %s" % (self.make, self.model)


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=20)
    authors = models.ManyToManyField(Author)

    def __str__(self):
        return self.name
