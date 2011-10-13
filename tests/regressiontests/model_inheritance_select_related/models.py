"""
Regression tests for the interaction between model inheritance and
select_related().
"""

from django.db import models


class Place(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return u"%s the place" % self.name

class Restaurant(Place):
    serves_sushi = models.BooleanField()
    serves_steak = models.BooleanField()

    def __unicode__(self):
        return u"%s the restaurant" % self.name

class Person(models.Model):
    name = models.CharField(max_length=50)
    favorite_restaurant = models.ForeignKey(Restaurant)

    def __unicode__(self):
        return self.name
