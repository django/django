from django.contrib.gis.db import models

class Location(models.Model):
    name = models.CharField(max_length=50)
    point = models.PointField()
    objects = models.GeoManager()

class City(models.Model):
    name = models.CharField(max_length=50)
    state = models.USStateField()
    location = models.ForeignKey(Location)
    objects = models.GeoManager()
