from __future__ import unicode_literals

import os

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils._os import upath


class Person(models.Model):
    name = models.CharField(max_length=100)

class Triple(models.Model):
    left = models.IntegerField()
    middle = models.IntegerField()
    right = models.IntegerField()

    class Meta:
        unique_together = (('left', 'middle'), ('middle', 'right'))

class FilePathModel(models.Model):
    path = models.FilePathField(path=os.path.dirname(upath(__file__)), match=".*\.py$", blank=True)

@python_2_unicode_compatible
class Publication(models.Model):
    title = models.CharField(max_length=30)
    date_published = models.DateField()

    def __str__(self):
        return self.title

@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(Publication)

    def __str__(self):
        return self.headline

class CustomFileField(models.FileField):
    def save_form_data(self, instance, data):
        been_here = getattr(self, 'been_saved', False)
        assert not been_here, "save_form_data called more than once"
        setattr(self, 'been_saved', True)

class CustomFF(models.Model):
    f = CustomFileField(upload_to='unused', blank=True)

class RealPerson(models.Model):
    name = models.CharField(max_length=100)

    def clean(self):
        if self.name.lower() == 'anonymous':
            raise ValidationError("Please specify a real name.")

class Author(models.Model):
    publication = models.OneToOneField(Publication, null=True, blank=True)
    full_name = models.CharField(max_length=255)

class Author1(models.Model):
    publication = models.OneToOneField(Publication, null=False)
    full_name = models.CharField(max_length=255)

class Homepage(models.Model):
    url = models.URLField()

class Document(models.Model):
    myfile = models.FileField(upload_to='unused', blank=True)

class Edition(models.Model):
    author = models.ForeignKey(Person)
    publication = models.ForeignKey(Publication)
    edition = models.IntegerField()
    isbn = models.CharField(max_length=13, unique=True)

    class Meta:
        unique_together = (('author', 'publication'), ('publication', 'edition'),)
