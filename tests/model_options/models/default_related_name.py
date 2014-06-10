
from django.db import models


class Author(models.Model):
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)


class Editor(models.Model):
    name = models.CharField(max_length=128)
    bestselling_author = models.ForeignKey(Author, null=True, blank=True)


class Book(models.Model):
    class Meta:
        default_related_name = "books"
    title = models.CharField(max_length=128)
    authors = models.ManyToManyField(Author)
    editor = models.ForeignKey(Editor, related_name="edited_books")


class Store(models.Model):
    class Meta:
        abstract = True
        default_related_name = "%(app_label)s_%(class)ss"
    name = models.CharField(max_length=128)
    address = models.CharField(max_length=128)


class BookStore(Store):
    available_books = models.ManyToManyField(Book)


class EditorStore(Store):
    class Meta:
        default_related_name = "editor_stores"
    editor = models.ForeignKey(Editor)
    available_books = models.ManyToManyField(Book)
