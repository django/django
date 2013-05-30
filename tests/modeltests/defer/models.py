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
    profile1 = models.TextField(default='profile1')

class Location(models.Model):
    location1 = models.TextField(default='location1')

class Item(models.Model):
    pass

class Request(models.Model):
    profile = models.ForeignKey(Profile, null=True, blank=True)
    location = models.ForeignKey(Location)
    items = models.ManyToManyField(Item)

    request1 = models.TextField(default='request1')
    request2 = models.TextField(default='request2')
    request3 = models.TextField(default='request3')
    request4 = models.TextField(default='request4')
