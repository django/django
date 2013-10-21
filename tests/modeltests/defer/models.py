"""
Tests for defer() and only().
"""

from django.db import models
from django.utils.encoding import python_2_unicode_compatible


class Secondary(models.Model):
    first = models.CharField(max_length=50)
    second = models.CharField(max_length=50)

@python_2_unicode_compatible
class Primary(models.Model):
    name = models.CharField(max_length=50)
    value = models.CharField(max_length=50)
    related = models.ForeignKey(Secondary)

    def __str__(self):
        return self.name

class Child(Primary):
    pass

class BigChild(Primary):
    other = models.CharField(max_length=50)

class ChildProxy(Child):
    class Meta:
        proxy=True

class Profile(models.Model):
    profile1 = models.CharField(max_length=1000, default='profile1')

class Location(models.Model):
    location1 = models.CharField(max_length=1000, default='location1')

class Item(models.Model):
    pass

class Request(models.Model):
    profile = models.ForeignKey(Profile, null=True, blank=True)
    location = models.ForeignKey(Location)
    items = models.ManyToManyField(Item)

    request1 = models.CharField(default='request1', max_length=1000)
    request2 = models.CharField(default='request2', max_length=1000)
    request3 = models.CharField(default='request3', max_length=1000)
    request4 = models.CharField(default='request4', max_length=1000)
