import os
from django.db import models

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
