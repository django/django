"""
Regression tests for the interaction between model inheritance and
select_related().
"""

from __future__ import unicode_literals

from django.db import models


class Place(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return "%s the place" % self.name

class Restaurant(Place):
    serves_sushi = models.BooleanField()
    serves_steak = models.BooleanField()

    def __unicode__(self):
        return "%s the restaurant" % self.name

class Person(models.Model):
    name = models.CharField(max_length=50)
    favorite_restaurant = models.ForeignKey(Restaurant)

    def __unicode__(self):
        return self.name
