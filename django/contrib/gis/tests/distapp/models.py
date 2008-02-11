from django.contrib.gis.db import models

class SouthTexasCity(models.Model):
    "City model on projected coordinate system for South Texas."
    name = models.CharField(max_length=30)
    point = models.PointField(srid=32140)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class AustraliaCity(models.Model):
    "City model for Australia, using WGS84."
    name = models.CharField(max_length=30)
    point = models.PointField()
    objects = models.GeoManager()
    def __unicode__(self): return self.name

#class County(models.Model):
#    name = models.CharField(max_length=30)
#    mpoly = models.MultiPolygonField(srid=32140)
#    objects = models.GeoManager()
