from django.contrib.gis.db import models

class Country(models.Model):
    name = models.CharField(max_length=30)
    mpoly = models.MultiPolygonField() # SRID, by default, is 4326
    objects = models.GeoManager()

class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField() 
    objects = models.GeoManager()

class State(models.Model):
    name = models.CharField(max_length=30)
    poly = models.PolygonField(null=True) # Allowing NULL geometries here.
    objects = models.GeoManager()

class Feature(models.Model):
    name = models.CharField(max_length=20)
    geom = models.GeometryField()
    objects = models.GeoManager()
