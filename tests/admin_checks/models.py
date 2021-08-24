"""
Tests of ModelAdmin system checks logic.
"""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Album(models.Model):
    title = models.CharField(max_length=150)


class Song(models.Model):
    title = models.CharField(max_length=150)
    album = models.ForeignKey(Album, models.CASCADE)
    original_release = models.DateField(editable=False)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title

    def readonly_method_on_model(self):
        # does nothing
        pass


class TwoAlbumFKAndAnE(models.Model):
    album1 = models.ForeignKey(Album, models.CASCADE, related_name="album1_set")
    album2 = models.ForeignKey(Album, models.CASCADE, related_name="album2_set")
    e = models.CharField(max_length=1)


class Author(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    name = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=100)
    price = models.FloatField()
    authors = models.ManyToManyField(Author, through="AuthorsBooks")


class AuthorsBooks(models.Model):
    author = models.ForeignKey(Author, models.CASCADE)
    book = models.ForeignKey(Book, models.CASCADE)
    featured = models.BooleanField()


class State(models.Model):
    name = models.CharField(max_length=15)


class City(models.Model):
    state = models.ForeignKey(State, models.CASCADE)


class Influence(models.Model):
    name = models.TextField()

    content_type = models.ForeignKey(ContentType, models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
