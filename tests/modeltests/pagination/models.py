"""
30. Object pagination

Django provides a framework for paginating a list of objects in a few lines
of code. This is often useful for dividing search results or long lists of
objects into easily readable pages.
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __str__(self):
        return self.headline
