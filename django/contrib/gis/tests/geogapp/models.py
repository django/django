from django.contrib.gis.db import models

class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField(geography=True)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class Zipcode(models.Model):
    code = models.CharField(max_length=10)
    poly = models.PolygonField(geography=True)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

class County(models.Model):
    name = models.CharField(max_length=25)
    state = models.CharField(max_length=20)
    mpoly = models.MultiPolygonField(geography=True)
    objects = models.GeoManager()
    def __unicode__(self): return ' County, '.join([self.name, self.state])
