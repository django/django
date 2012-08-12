"""
Comments may be attached to any object. See the comment documentation for
more information.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

@python_2_unicode_compatible
class Article(models.Model):
    author = models.ForeignKey(Author)
    headline = models.CharField(max_length=100)

    def __str__(self):
        return self.headline

@python_2_unicode_compatible
class Entry(models.Model):
    title = models.CharField(max_length=250)
    body = models.TextField()
    pub_date = models.DateField()
    enable_comments = models.BooleanField()

    def __str__(self):
        return self.title

class Book(models.Model):
    dewey_decimal = models.DecimalField(primary_key=True, decimal_places=2, max_digits=5)
