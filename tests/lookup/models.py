"""
The lookup API

This demonstrates features of the database API.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible


class Alarm(models.Model):
    desc = models.CharField(max_length=100)
    time = models.TimeField()

    def __str__(self):
        return '%s (%s)' % (self.time, self.desc)


class Author(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name', )


@python_2_unicode_compatible
class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    author = models.ForeignKey(Author, models.SET_NULL, blank=True, null=True)

    class Meta:
        ordering = ('-pub_date', 'headline')

    def __str__(self):
        return self.headline


class Tag(models.Model):
    articles = models.ManyToManyField(Article)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ('name', )


@python_2_unicode_compatible
class Season(models.Model):
    year = models.PositiveSmallIntegerField()
    gt = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return six.text_type(self.year)


@python_2_unicode_compatible
class Game(models.Model):
    season = models.ForeignKey(Season, models.CASCADE, related_name='games')
    home = models.CharField(max_length=100)
    away = models.CharField(max_length=100)

    def __str__(self):
        return "%s at %s" % (self.away, self.home)


@python_2_unicode_compatible
class Player(models.Model):
    name = models.CharField(max_length=100)
    games = models.ManyToManyField(Game, related_name='players')

    def __str__(self):
        return self.name


# To test __search lookup a fulltext index is needed. This
# is only available when using MySQL 5.6, or when using MyISAM
# tables. As 5.6 isn't common yet, lets use MyISAM table for
# testing. The table is manually created by the test method.
# RemovedInDjango20Warning
class MyISAMArticle(models.Model):
    headline = models.CharField(max_length=100)

    class Meta:
        db_table = 'myisam_article'
        managed = False


class Product(models.Model):
    name = models.CharField(max_length=80)
    qty_target = models.DecimalField(max_digits=6, decimal_places=2)


class Stock(models.Model):
    product = models.ForeignKey(Product, models.CASCADE)
    qty_available = models.DecimalField(max_digits=6, decimal_places=2)
