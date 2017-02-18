from django.utils.encoding import python_2_unicode_compatible

from ..models import models
from ..utils import gisfield_may_be_null


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    objects = models.GeoManager()

    class Meta:
        abstract = True
        required_db_features = ['gis_enabled']

    def __str__(self):
        return self.name


class Country(NamedModel):
    mpoly = models.MultiPolygonField()  # SRID, by default, is 4326


class City(NamedModel):
    point = models.PointField()

    class Meta:
        app_label = 'geoapp'
        required_db_features = ['gis_enabled']


# This is an inherited model from City
class PennsylvaniaCity(City):
    county = models.CharField(max_length=30)
    founded = models.DateTimeField(null=True)

    # TODO: This should be implicitly inherited.

    objects = models.GeoManager()

    class Meta:
        app_label = 'geoapp'
        required_db_features = ['gis_enabled']


class State(NamedModel):
    poly = models.PolygonField(null=gisfield_may_be_null)  # Allowing NULL geometries here.

    class Meta:
        app_label = 'geoapp'
        required_db_features = ['gis_enabled']


class Track(NamedModel):
    line = models.LineStringField()


class MultiFields(NamedModel):
    city = models.ForeignKey(City)
    point = models.PointField()
    poly = models.PolygonField()

    class Meta:
        unique_together = ('city', 'point')
        required_db_features = ['gis_enabled']


class Truth(models.Model):
    val = models.BooleanField(default=False)

    objects = models.GeoManager()

    class Meta:
        required_db_features = ['gis_enabled']


class Feature(NamedModel):
    geom = models.GeometryField()


class MinusOneSRID(models.Model):
    geom = models.PointField(srid=-1)  # Minus one SRID.

    objects = models.GeoManager()

    class Meta:
        required_db_features = ['gis_enabled']


class NonConcreteField(models.IntegerField):

    def db_type(self, connection):
        return None

    def get_attname_column(self):
        attname, column = super(NonConcreteField, self).get_attname_column()
        return attname, None


class NonConcreteModel(NamedModel):
    non_concrete = NonConcreteField()
    point = models.PointField(geography=True)
