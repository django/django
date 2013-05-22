from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
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

@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=300)
    slug = models.SlugField()
    pages = models.IntegerField()
    authors = models.ManyToManyField(Author)
    pubdate = models.DateField()

    class Meta:
        ordering = ['-pubdate']

    def __str__(self):
        return self.name

class Page(models.Model):
    content = models.TextField()
    template = models.CharField(max_length=300)

class BookSigning(models.Model):
    event_date = models.DateTimeField()
