from django.contrib.gis.db import models

class State(models.Model):
    name = models.CharField(max_length=20)
    objects = models.GeoManager()

class County(models.Model):
    name = models.CharField(max_length=25)
    state = models.ForeignKey(State)
    mpoly = models.MultiPolygonField(srid=4269) # Multipolygon in NAD83
    objects = models.GeoManager()

class CountyFeat(models.Model):
    name = models.CharField(max_length=25)
    poly = models.PolygonField(srid=4269)
    objects = models.GeoManager()

class City(models.Model):
    name = models.CharField(max_length=25)
    name_txt = models.TextField(default='')
    population = models.IntegerField()
    density = models.DecimalField(max_digits=7, decimal_places=1)
    dt = models.DateField()
    point = models.PointField()
    objects = models.GeoManager()

class Interstate(models.Model):
    name = models.CharField(max_length=20)
    length = models.DecimalField(max_digits=6, decimal_places=2)
    path = models.LineStringField()
    objects = models.GeoManager()

# Same as `City` above, but for testing model inheritance.
class CityBase(models.Model):
    name = models.CharField(max_length=25)
    population = models.IntegerField()
    density = models.DecimalField(max_digits=7, decimal_places=1)
    point = models.PointField()
    objects = models.GeoManager()

class ICity1(CityBase):
    dt = models.DateField()
    
class ICity2(ICity1):
    dt_time = models.DateTimeField(auto_now=True)

class Invalid(models.Model):
    point = models.PointField()

# Mapping dictionaries for the models above.
co_mapping = {'name' : 'Name',
              'state' : {'name' : 'State'}, # ForeignKey's use another mapping dictionary for the _related_ Model (State in this case).
              'mpoly' : 'MULTIPOLYGON', # Will convert POLYGON features into MULTIPOLYGONS.
              }

cofeat_mapping = {'name' : 'Name',
                  'poly' : 'POLYGON',
                  }

city_mapping = {'name' : 'Name',
                'population' : 'Population',
                'density' : 'Density',
                'dt' : 'Created',
                'point' : 'POINT',
                }

inter_mapping = {'name' : 'Name',
                 'length' : 'Length',
                 'path' : 'LINESTRING',
                 }
