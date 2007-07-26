from django.contrib.gis.db import models

class Country(models.Model, models.GeoMixin):
    name = models.CharField(maxlength=30)
    mpoly = models.MultiPolygonField() # SRID, by default, is 4326
    objects = models.GeoManager()

class City(models.Model, models.GeoMixin):
    name = models.CharField(maxlength=30)
    point = models.PointField() 
    objects = models.GeoManager()
