from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=20)
    authors = models.ManyToManyField(Author)

    def __str__(self):
        return self.name
