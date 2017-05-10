from django.db import models
from django.db.models import QuerySet
from django.db.models.manager import BaseManager
from django.urls import reverse


class Artist(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']
        verbose_name = 'professional artist'
        verbose_name_plural = 'professional artists'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('artist_detail', kwargs={'pk': self.id})


class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DoesNotExistQuerySet(QuerySet):
    def get(self, *args, **kwargs):
        raise Author.DoesNotExist


DoesNotExistBookManager = BaseManager.from_queryset(DoesNotExistQuerySet)


class Book(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    pages = models.IntegerField()
    authors = models.ManyToManyField(Author)
    pubdate = models.DateField()

    objects = models.Manager()
    does_not_exist = DoesNotExistBookManager()

    class Meta:
        ordering = ['-pubdate']

    def __str__(self):
        return self.name


class Page(models.Model):
    content = models.TextField()
    template = models.CharField(max_length=255)


class BookSigning(models.Model):
    event_date = models.DateTimeField()
