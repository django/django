from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=50, unique=True)
    favourite_books = models.ManyToManyField(
        'Book',
        related_name='preferred_by_authors',
        related_query_name='preferred_by_authors')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


@python_2_unicode_compatible
class Editor(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']


@python_2_unicode_compatible
class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author,
                               related_name='books',
                               related_query_name='book',
                               on_delete=models.CASCADE)
    editor = models.ForeignKey(Editor, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['id']
