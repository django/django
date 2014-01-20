from django.contrib.gis.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=25)

    objects = models.GeoManager()

    class Meta:
        abstract = True
        app_label = 'layermap'

    def __str__(self):
        return self.name


class State(NamedModel):
    pass


class County(NamedModel):
    state = models.ForeignKey(State)
    mpoly = models.MultiPolygonField(srid=4269)  # Multipolygon in NAD83


class CountyFeat(NamedModel):
    poly = models.PolygonField(srid=4269)


class City(NamedModel):
    name_txt = models.TextField(default='')
    population = models.IntegerField()
    density = models.DecimalField(max_digits=7, decimal_places=1)
    dt = models.DateField()
    point = models.PointField()


class Interstate(NamedModel):
    length = models.DecimalField(max_digits=6, decimal_places=2)
    path = models.LineStringField()


# Same as `City` above, but for testing model inheritance.
class CityBase(NamedModel):
    population = models.IntegerField()
    density = models.DecimalField(max_digits=7, decimal_places=1)
    point = models.PointField()


class ICity1(CityBase):
    dt = models.DateField()

    class Meta(CityBase.Meta):
        pass


class ICity2(ICity1):
    dt_time = models.DateTimeField(auto_now=True)

    class Meta(ICity1.Meta):
        pass


class Invalid(models.Model):
    point = models.PointField()

    class Meta:
        app_label = 'layermap'


# Mapping dictionaries for the models above.
co_mapping = {'name': 'Name',
              'state': {'name': 'State'},  # ForeignKey's use another mapping dictionary for the _related_ Model (State in this case).
              'mpoly': 'MULTIPOLYGON',  # Will convert POLYGON features into MULTIPOLYGONS.
              }

cofeat_mapping = {'name': 'Name',
                  'poly': 'POLYGON',
                  }

city_mapping = {'name': 'Name',
                'population': 'Population',
                'density': 'Density',
                'dt': 'Created',
                'point': 'POINT',
                }

inter_mapping = {'name': 'Name',
                 'length': 'Length',
                 'path': 'LINESTRING',
                 }
