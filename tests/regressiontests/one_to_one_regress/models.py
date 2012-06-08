from __future__ import unicode_literals

from django.db import models


class Place(models.Model):
    name = models.CharField(max_length=50)
    address = models.CharField(max_length=80)

    def __unicode__(self):
        return "%s the place" % self.name

class Restaurant(models.Model):
    place = models.OneToOneField(Place)
    serves_hot_dogs = models.BooleanField()
    serves_pizza = models.BooleanField()

    def __unicode__(self):
        return "%s the restaurant" % self.place.name

class Bar(models.Model):
    place = models.OneToOneField(Place)
    serves_cocktails = models.BooleanField()

    def __unicode__(self):
        return "%s the bar" % self.place.name

class UndergroundBar(models.Model):
    place = models.OneToOneField(Place, null=True)
    serves_cocktails = models.BooleanField()

class Favorites(models.Model):
    name = models.CharField(max_length = 50)
    restaurants = models.ManyToManyField(Restaurant)

    def __unicode__(self):
        return "Favorites for %s" % self.name

class Target(models.Model):
    pass

class Pointer(models.Model):
    other = models.OneToOneField(Target, primary_key=True)

class Pointer2(models.Model):
    other = models.OneToOneField(Target)
