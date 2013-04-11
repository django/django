"""
Regression tests for Django built-in views.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return '/views/authors/%s/' % self.id

@python_2_unicode_compatible
class BaseArticle(models.Model):
    """
    An abstract article Model so that we can create article models with and
    without a get_absolute_url method (for create_update generic views tests).
    """
    title = models.CharField(max_length=100)
    slug = models.SlugField()
    author = models.ForeignKey(Author)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

class Article(BaseArticle):
    date_created = models.DateTimeField()

class UrlArticle(BaseArticle):
    """
    An Article class with a get_absolute_url defined.
    """
    date_created = models.DateTimeField()

    def get_absolute_url(self):
        return '/urlarticles/%s/' % self.slug
    get_absolute_url.purge = True

class DateArticle(BaseArticle):
    """
    An article Model with a DateField instead of DateTimeField,
    for testing #7602
    """
    date_created = models.DateField()
