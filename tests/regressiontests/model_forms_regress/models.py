import os
from django.db import models
from django.core.exceptions import ValidationError


class Person(models.Model):
    name = models.CharField(max_length=100)

class Triple(models.Model):
    left = models.IntegerField()
    middle = models.IntegerField()
    right = models.IntegerField()

    class Meta:
        unique_together = (('left', 'middle'), (u'middle', u'right'))

class FilePathModel(models.Model):
    path = models.FilePathField(path=os.path.dirname(__file__), match=".*\.py$", blank=True)

class Publication(models.Model):
    title = models.CharField(max_length=30)
    date_published = models.DateField()

    def __unicode__(self):
        return self.title

class Article(models.Model):
    headline = models.CharField(max_length=100)
    publications = models.ManyToManyField(Publication)

    def __unicode__(self):
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
    url = models.URLField(verify_exists=False)

class Document(models.Model):
    myfile = models.FileField(upload_to='unused', blank=True)
