from __future__ import unicode_literals

from django.db import models

class Author(models.Model):
    pass

class Publisher(models.Model):
    pass

class Book(models.Model):
    authors = models.ManyToManyField(Author)
    publisher = models.ForeignKey(Publisher)
