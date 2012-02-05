"""
7. The lookup API

This demonstrates features of the database API.
"""

from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
    class Meta:
        ordering = ('name', )

class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateTimeField()
    author = models.ForeignKey(Author, blank=True, null=True)
    class Meta:
        ordering = ('-pub_date', 'headline')

    def __unicode__(self):
        return self.headline

class Tag(models.Model):
    articles = models.ManyToManyField(Article)
    name = models.CharField(max_length=100)
    class Meta:
        ordering = ('name', )

class Season(models.Model):
    year = models.PositiveSmallIntegerField()
    gt = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return unicode(self.year)

class Game(models.Model):
    season = models.ForeignKey(Season, related_name='games')
    home = models.CharField(max_length=100)
    away = models.CharField(max_length=100)

    def __unicode__(self):
        return u"%s at %s" % (self.away, self.home)

class Player(models.Model):
    name = models.CharField(max_length=100)
    games = models.ManyToManyField(Game, related_name='players')

    def __unicode__(self):
        return self.name