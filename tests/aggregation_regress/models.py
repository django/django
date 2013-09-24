# coding: utf-8
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    friends = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Publisher(models.Model):
    name = models.CharField(max_length=255)
    num_awards = models.IntegerField()

    def __str__(self):
        return self.name


class ItemTag(models.Model):
    tag = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')


@python_2_unicode_compatible
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
    tags = generic.GenericRelation(ItemTag)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Store(models.Model):
    name = models.CharField(max_length=255)
    books = models.ManyToManyField(Book)
    original_opening = models.DateTimeField()
    friday_night_closing = models.TimeField()

    def __str__(self):
        return self.name

class Entries(models.Model):
    EntryID = models.AutoField(primary_key=True, db_column='Entry ID')
    Entry = models.CharField(unique=True, max_length=50)
    Exclude = models.BooleanField(default=False)


class Clues(models.Model):
    ID = models.AutoField(primary_key=True)
    EntryID = models.ForeignKey(Entries, verbose_name='Entry', db_column = 'Entry ID')
    Clue = models.CharField(max_length=150)


class WithManualPK(models.Model):
    # The generic relations regression test needs two different model
    # classes with the same PK value, and there are some (external)
    # DB backends that don't work nicely when assigning integer to AutoField
    # column (MSSQL at least).
    id = models.IntegerField(primary_key=True)


@python_2_unicode_compatible
class HardbackBook(Book):
    weight = models.FloatField()

    def __str__(self):
        return "%s (hardback): %s" % (self.name, self.weight)

# Models for ticket #21150
class Alfa(models.Model):
    pass

class Bravo(models.Model):
    pass

class Charlie(models.Model):
    alfa = models.ForeignKey(Alfa, null=True)
    bravo = models.ForeignKey(Bravo, null=True)
