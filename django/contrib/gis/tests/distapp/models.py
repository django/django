from django.contrib.gis.db import models

class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField(srid=32140)
    objects = models.GeoManager()
    def __unicode__(self): return self.name

#class County(models.Model):
#    name = models.CharField(max_length=30)
#    mpoly = models.MultiPolygonField(srid=32140)
#    objects = models.GeoManager()

city_mapping = {'name' : 'Name',
                'point' : 'POINT',
                }

#county_mapping = {'name' : 'Name',
#                  'mpoly' : 'MULTIPOLYGON',
#                  }
