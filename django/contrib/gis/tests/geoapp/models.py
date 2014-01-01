from django.contrib.gis.db import models
from django.contrib.gis.tests.utils import mysql, spatialite
from django.utils.encoding import python_2_unicode_compatible

# MySQL spatial indices can't handle NULL geometries.
null_flag = not mysql


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    objects = models.GeoManager()

    class Meta:
        abstract = True
        app_label = 'geoapp'

    def __str__(self):
        return self.name


class Country(NamedModel):
    mpoly = models.MultiPolygonField()  # SRID, by default, is 4326


class City(NamedModel):
    point = models.PointField()


# This is an inherited model from City
class PennsylvaniaCity(City):
    county = models.CharField(max_length=30)
    founded = models.DateTimeField(null=True)

    # TODO: This should be implicitly inherited.

    objects = models.GeoManager()

    class Meta:
        app_label = 'geoapp'


class State(NamedModel):
    poly = models.PolygonField(null=null_flag)  # Allowing NULL geometries here.


class Track(NamedModel):
    line = models.LineStringField()


class Truth(models.Model):
    val = models.BooleanField(default=False)

    objects = models.GeoManager()

    class Meta:
        app_label = 'geoapp'


if not spatialite:

    class Feature(NamedModel):
        geom = models.GeometryField()

    class MinusOneSRID(models.Model):
        geom = models.PointField(srid=-1)  # Minus one SRID.

        objects = models.GeoManager()

        class Meta:
            app_label = 'geoapp'
