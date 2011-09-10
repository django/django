from django.contrib.gis.db import models
from django.contrib.gis import admin

class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()
    objects = models.GeoManager()
    def __unicode__(self): return self.name

admin.site.register(City, admin.OSMGeoAdmin)
