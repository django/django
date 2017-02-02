from django.db import models


class Author(models.Model):
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128)


class Editor(models.Model):
    name = models.CharField(max_length=128)
    bestselling_author = models.ForeignKey(Author, models.CASCADE)


class Book(models.Model):
    title = models.CharField(max_length=128)
    authors = models.ManyToManyField(Author)
    editor = models.ForeignKey(Editor, models.CASCADE, related_name="edited_books")

    class Meta:
        default_related_name = "books"


class Store(models.Model):
    name = models.CharField(max_length=128)
    address = models.CharField(max_length=128)

    class Meta:
        abstract = True
        default_related_name = "%(app_label)s_%(model_name)ss"


class BookStore(Store):
    available_books = models.ManyToManyField(Book)


class EditorStore(Store):
    editor = models.ForeignKey(Editor, models.CASCADE)
    available_books = models.ManyToManyField(Book)

    class Meta:
        default_related_name = "editor_stores"
