# coding: utf-8
import pickle

from django.db import connection, models, DEFAULT_DB_ALIAS
from django.conf import settings


class Author(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    friends = models.ManyToManyField('self', blank=True)

    def __unicode__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(max_length=255)
    num_awards = models.IntegerField()

    def __unicode__(self):
        return self.name


class Book(models.Model):
    isbn = models.CharField(max_length=9)
    name = models.CharField(max_length=255)
    pages = models.IntegerField()
    rating = models.FloatField()
    price = models.DecimalField(decimal_places=2, max_digits=6)
    authors = models.ManyToManyField(Author)
    contact = models.ForeignKey(Author, related_name='book_contact_set')
    publisher = models.ForeignKey(Publisher)
    pubdate = models.DateField()

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Store(models.Model):
    name = models.CharField(max_length=255)
    books = models.ManyToManyField(Book)
    original_opening = models.DateTimeField()
    friday_night_closing = models.TimeField()

    def __unicode__(self):
        return self.name


class Entries(models.Model):
    EntryID = models.AutoField(primary_key=True, db_column='Entry ID')
    Entry = models.CharField(unique=True, max_length=50)
    Exclude = models.BooleanField()


class Clues(models.Model):
    ID = models.AutoField(primary_key=True)
    EntryID = models.ForeignKey(Entries, verbose_name='Entry', db_column = 'Entry ID')
    Clue = models.CharField(max_length=150)


class HardbackBook(Book):
    weight = models.FloatField()

    def __unicode__(self):
        return "%s (hardback): %s" % (self.name, self.weight)
