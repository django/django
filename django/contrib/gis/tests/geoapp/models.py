from django.contrib.gis.db import models
from django.contrib.gis.tests.utils import mysql

# MySQL spatial indices can't handle NULL geometries.
null_flag = not mysql

class Country(models.Model):
    name = models.CharField(max_length=30)
    mpoly = models.MultiPolygonField() # SRID, by default, is 4326
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField() 
    objects = models.GeoManager()
    def __unicode__(self): return self.name

# This is an inherited model from City
class PennsylvaniaCity(City):
    county = models.CharField(max_length=30)
    objects = models.GeoManager() # TODO: This should be implicitly inherited.

class State(models.Model):
    name = models.CharField(max_length=30)
    poly = models.PolygonField(null=null_flag) # Allowing NULL geometries here.
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class Feature(models.Model):
    name = models.CharField(max_length=20)
    geom = models.GeometryField()
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class MinusOneSRID(models.Model):
    geom = models.PointField(srid=-1) # Minus one SRID.
    objects = models.GeoManager()
