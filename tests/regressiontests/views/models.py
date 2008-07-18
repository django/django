"""
Regression tests for Django built-in views.
"""

from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return '/views/authors/%s/' % self.id

class BaseArticle(models.Model):
    """
    An abstract article Model so that we can create article models with and
    without a get_absolute_url method (for create_update generic views tests).
    """
    title = models.CharField(max_length=100)
    slug = models.SlugField()
    author = models.ForeignKey(Author)
    date_created = models.DateTimeField()

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.title

class Article(BaseArticle):
    pass

class UrlArticle(BaseArticle):
    """
    An Article class with a get_absolute_url defined.
    """
    def get_absolute_url(self):
        return '/urlarticles/%s/' % self.slug
