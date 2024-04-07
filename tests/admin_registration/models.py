"""
Tests for various ways of registering models with the admin site.
"""

from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=200)


class Traveler(Person):
    pass


class Location(models.Model):
    class Meta:
        abstract = True


class Place(Location):
    name = models.CharField(max_length=200)


class Guest(models.Model):
    pk = models.CompositePrimaryKey("traveler", "place")
    traveler = models.ForeignKey(Traveler, on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
