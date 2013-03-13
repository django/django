from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


class Tag(models.Model):
    name = models.CharField(max_length=255)


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=200)
    pages = models.IntegerField(default=0)
    author = models.ForeignKey(Author, null=True)
    pubdate = models.DateTimeField()
    tags = models.ManyToManyField(Tag)

    class Meta:
        ordering = ['-pubdate', 'name']

    def __str__(self):
        return self.name
