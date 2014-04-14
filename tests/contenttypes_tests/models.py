from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return '/authors/%s/' % self.id


@python_2_unicode_compatible
class Article(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField()
    author = models.ForeignKey(Author)
    date_created = models.DateTimeField()

    def __str__(self):
        return self.title


@python_2_unicode_compatible
class SchemeIncludedURL(models.Model):
    url = models.URLField(max_length=100)

    def __str__(self):
        return self.url

    def get_absolute_url(self):
        return self.url
