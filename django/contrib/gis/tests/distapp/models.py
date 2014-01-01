from django.contrib.gis.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    objects = models.GeoManager()

    class Meta:
        abstract = True
        app_label = 'distapp'

    def __str__(self):
        return self.name


class SouthTexasCity(NamedModel):
    "City model on projected coordinate system for South Texas."
    point = models.PointField(srid=32140)


class SouthTexasCityFt(NamedModel):
    "Same City model as above, but U.S. survey feet are the units."
    point = models.PointField(srid=2278)


class AustraliaCity(NamedModel):
    "City model for Australia, using WGS84."
    point = models.PointField()


class CensusZipcode(NamedModel):
    "Model for a few South Texas ZIP codes (in original Census NAD83)."
    name = models.CharField(max_length=5)
    poly = models.PolygonField(srid=4269)


class SouthTexasZipcode(NamedModel):
    "Model for a few South Texas ZIP codes."
    name = models.CharField(max_length=5)
    poly = models.PolygonField(srid=32140, null=True)


class Interstate(NamedModel):
    "Geodetic model for U.S. Interstates."
    name = models.CharField(max_length=10)
    path = models.LineStringField()


class SouthTexasInterstate(NamedModel):
    "Projected model for South Texas Interstates."
    name = models.CharField(max_length=10)

