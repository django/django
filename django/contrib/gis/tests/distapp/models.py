from django.contrib.gis.db import models

class SouthTexasCity(models.Model):
    "City model on projected coordinate system for South Texas."
    name = models.CharField(max_length=30)
    point = models.PointField(srid=32140)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class SouthTexasCityFt(models.Model):
    "Same City model as above, but U.S. survey feet are the units."
    name = models.CharField(max_length=30)
    point = models.PointField(srid=2278)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class AustraliaCity(models.Model):
    "City model for Australia, using WGS84."
    name = models.CharField(max_length=30)
    point = models.PointField()
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class CensusZipcode(models.Model):
    "Model for a few South Texas ZIP codes (in original Census NAD83)."
    name = models.CharField(max_length=5)
    poly = models.PolygonField(srid=4269)
    objects = models.GeoManager()

class SouthTexasZipcode(models.Model):
    "Model for a few South Texas ZIP codes."
    name = models.CharField(max_length=5)
    poly = models.PolygonField(srid=32140)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class Interstate(models.Model):
    "Geodetic model for U.S. Interstates."
    name = models.CharField(max_length=10)
    line = models.LineStringField()
    objects = models.GeoManager()
    def __unicode__(self): return self.name
