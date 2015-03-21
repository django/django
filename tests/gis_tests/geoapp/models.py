from django.contrib.gis.db import models
from django.utils.encoding import python_2_unicode_compatible

from ..utils import gisfield_may_be_null


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    objects = models.GeoManager()

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Country(NamedModel):
    mpoly = models.MultiPolygonField()  # SRID, by default, is 4326


class City(NamedModel):
    point = models.PointField()

    class Meta:
        app_label = 'geoapp'


# This is an inherited model from City
class PennsylvaniaCity(City):
    county = models.CharField(max_length=30)
    founded = models.DateTimeField(null=True)

    # TODO: This should be implicitly inherited.

    objects = models.GeoManager()

    class Meta:
        app_label = 'geoapp'


class State(NamedModel):
    poly = models.PolygonField(null=gisfield_may_be_null)  # Allowing NULL geometries here.

    class Meta:
        app_label = 'geoapp'


class Track(NamedModel):
    line = models.LineStringField()


class MultiFields(NamedModel):
    city = models.ForeignKey(City)
    point = models.PointField()
    poly = models.PolygonField()


class Truth(models.Model):
    val = models.BooleanField(default=False)

    objects = models.GeoManager()


class Feature(NamedModel):
    geom = models.GeometryField()


class MinusOneSRID(models.Model):
    geom = models.PointField(srid=-1)  # Minus one SRID.

    objects = models.GeoManager()


class NonConcreteField(models.IntegerField):

    def db_type(self, connection):
        return None

    def get_attname_column(self):
        attname, column = super(NonConcreteField, self).get_attname_column()
        return attname, None


class NonConcreteModel(NamedModel):
    non_concrete = NonConcreteField()
    point = models.PointField(geography=True)
