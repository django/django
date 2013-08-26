"""
Tests of ModelAdmin validation logic.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Album(models.Model):
    title = models.CharField(max_length=150)


@python_2_unicode_compatible
class Song(models.Model):
    title = models.CharField(max_length=150)
    album = models.ForeignKey(Album)
    original_release = models.DateField(editable=False)

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return self.title

    def readonly_method_on_model(self):
        # does nothing
        pass


class TwoAlbumFKAndAnE(models.Model):
    album1 = models.ForeignKey(Album, related_name="album1_set")
    album2 = models.ForeignKey(Album, related_name="album2_set")
    e = models.CharField(max_length=1)


class Author(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    name = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100)
    price = models.FloatField()
    authors = models.ManyToManyField(Author, through='AuthorsBooks')


class AuthorsBooks(models.Model):
    author = models.ForeignKey(Author)
    book = models.ForeignKey(Book)


class State(models.Model):
    name = models.CharField(max_length=15)


class City(models.Model):
    state = models.ForeignKey(State)
