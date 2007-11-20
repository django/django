from django.contrib.gis.db import models

class City(models.Model):
    name = models.CharField(max_length=25)
    population = models.IntegerField()
    density = models.DecimalField(max_digits=7, decimal_places=1)
    date = models.DateField()
    point = models.PointField()
    objects = models.GeoManager()

class Interstate(models.Model):
    name = models.CharField(max_length=20)
    length = models.DecimalField(max_digits=6, decimal_places=2)
    path = models.LineStringField()
    objects = models.GeoManager()
    
# Mapping dictionary for the City model.
city_mapping = {'name' : 'Name',
                'population' : 'Population',
                'density' : 'Density',
                'date' : 'Created',
                'point' : 'POINT',
                }

# Mapping dictionary for the Interstate model.
inter_mapping = {'name' : 'Name',
                 'length' : 'Length',
                 'path' : 'LINESTRING',
                 }
