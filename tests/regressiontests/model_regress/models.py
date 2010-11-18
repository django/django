# coding: utf-8
from django.db import models


CHOICES = (
    (1, 'first'),
    (2, 'second'),
)

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()
    status = models.IntegerField(blank=True, null=True, choices=CHOICES)
    misc_data = models.CharField(max_length=100, blank=True)
    article_text = models.TextField()

    class Meta:
        ordering = ('pub_date','headline')
        # A utf-8 verbose name (Ångström's Articles) to test they are valid.
        verbose_name = "\xc3\x85ngstr\xc3\xb6m's Articles"

    def __unicode__(self):
        return self.headline

class Movie(models.Model):
    #5218: Test models with non-default primary keys / AutoFields
    movie_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=60)

class Party(models.Model):
    when = models.DateField(null=True)

class Event(models.Model):
    when = models.DateTimeField()

class Department(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class Worker(models.Model):
    department = models.ForeignKey(Department)
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class BrokenUnicodeMethod(models.Model):
    name = models.CharField(max_length=7)

    def __unicode__(self):
        # Intentionally broken (trying to insert a unicode value into a str
        # object).
        return 'Názov: %s' % self.name

class NonAutoPK(models.Model):
    name = models.CharField(max_length=10, primary_key=True)
