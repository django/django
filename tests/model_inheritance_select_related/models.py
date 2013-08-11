"""
Regression tests for the interaction between model inheritance and
select_related().
"""
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Place(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return "%s the place" % self.name

@python_2_unicode_compatible
class Restaurant(Place):
    serves_sushi = models.BooleanField(default=False)
    serves_steak = models.BooleanField(default=False)

    def __str__(self):
        return "%s the restaurant" % self.name

@python_2_unicode_compatible
class Person(models.Model):
    name = models.CharField(max_length=50)
    favorite_restaurant = models.ForeignKey(Restaurant)

    def __str__(self):
        return self.name
