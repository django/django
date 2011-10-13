# -*- coding: utf-8 -*-
"""
42. Serialization

``django.core.serializers`` provides interfaces to converting Django
``QuerySet`` objects to and from "flat" data (i.e. strings).
"""

from decimal import Decimal

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
       ordering = ('name',)

    def __unicode__(self):
        return self.name


class Author(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Article(models.Model):
    author = models.ForeignKey(Author)
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)

    class Meta:
       ordering = ('pub_date',)

    def __unicode__(self):
        return self.headline


class AuthorProfile(models.Model):
    author = models.OneToOneField(Author, primary_key=True)
    date_of_birth = models.DateField()

    def __unicode__(self):
        return u"Profile of %s" % self.author


class Actor(models.Model):
    name = models.CharField(max_length=20, primary_key=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Movie(models.Model):
    actor = models.ForeignKey(Actor)
    title = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
       ordering = ('title',)

    def __unicode__(self):
        return self.title


class Score(models.Model):
    score = models.FloatField()


class Team(object):
    def __init__(self, title):
        self.title = title

    def __unicode__(self):
        raise NotImplementedError("Not so simple")

    def __str__(self):
        raise NotImplementedError("Not so simple")

    def to_string(self):
        return "%s" % self.title


class TeamField(models.CharField):
    __metaclass__ = models.SubfieldBase

    def __init__(self):
        super(TeamField, self).__init__(max_length=100)

    def get_db_prep_save(self, value, connection):
        return unicode(value.title)

    def to_python(self, value):
        if isinstance(value, Team):
            return value
        return Team(value)

    def value_to_string(self, obj):
        return self._get_val_from_obj(obj).to_string()


class Player(models.Model):
    name = models.CharField(max_length=50)
    rank = models.IntegerField()
    team = TeamField()

    def __unicode__(self):
        return u'%s (%d) playing for %s' % (self.name, self.rank, self.team.to_string())
