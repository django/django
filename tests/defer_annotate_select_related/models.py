from django.db import models

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
