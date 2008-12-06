from django.contrib.gis.db import models
from django.contrib.localflavor.us.models import USStateField

class Location(models.Model):
    name = models.CharField(max_length=50)
    point = models.PointField()
    objects = models.GeoManager()

class City(models.Model):
    name = models.CharField(max_length=50)
    state = USStateField()
    location = models.ForeignKey(Location)
    objects = models.GeoManager()

class AugmentedLocation(Location):
    extra_text = models.TextField(blank=True)
    objects = models.GeoManager()
    
class DirectoryEntry(models.Model):
    listing_text = models.CharField(max_length=50)
    location = models.ForeignKey(AugmentedLocation)
    objects = models.GeoManager()
