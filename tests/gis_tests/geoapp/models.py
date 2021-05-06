from django.contrib.gis.db import models

from ..utils import gisfield_may_be_null


class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Country(NamedModel):
    mpoly = models.MultiPolygonField()  # SRID, by default, is 4326


class CountryWebMercator(NamedModel):
    mpoly = models.MultiPolygonField(srid=3857)


class City(NamedModel):
    point = models.PointField()

    class Meta:
        app_label = 'geoapp'


# This is an inherited model from City
class PennsylvaniaCity(City):
    county = models.CharField(max_length=30)
    founded = models.DateTimeField(null=True)

    class Meta:
        app_label = 'geoapp'


class State(NamedModel):
    poly = models.PolygonField(null=gisfield_may_be_null)  # Allowing NULL geometries here.

    class Meta:
        app_label = 'geoapp'


class Track(NamedModel):
    line = models.LineStringField()


class MultiFields(NamedModel):
    city = models.ForeignKey(City, models.CASCADE)
    point = models.PointField()
    poly = models.PolygonField()


class UniqueTogetherModel(models.Model):
    city = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        unique_together = ('city', 'point')
        required_db_features = ['supports_geometry_field_unique_index']


class Truth(models.Model):
    val = models.BooleanField(default=False)


class Feature(NamedModel):
    geom = models.GeometryField()


class MinusOneSRID(models.Model):
    geom = models.PointField(srid=-1)  # Minus one SRID.


class NonConcreteField(models.IntegerField):

    def db_type(self, connection):
        return None

    def get_attname_column(self):
        attname, column = super().get_attname_column()
        return attname, None


class NonConcreteModel(NamedModel):
    non_concrete = NonConcreteField()
    point = models.PointField(geography=True)


class ManyPointModel(NamedModel):
    point1 = models.PointField()
    point2 = models.PointField()
    point3 = models.PointField(srid=3857)
