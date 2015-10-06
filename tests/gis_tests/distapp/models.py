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


class SouthTexasCity(NamedModel):
    "City model on projected coordinate system for South Texas."
    point = models.PointField(srid=32140)
    radius = models.IntegerField(default=10000)


class SouthTexasCityFt(NamedModel):
    "Same City model as above, but U.S. survey feet are the units."
    point = models.PointField(srid=2278)


class AustraliaCity(NamedModel):
    "City model for Australia, using WGS84."
    point = models.PointField()
    radius = models.IntegerField(default=10000)


class CensusZipcode(NamedModel):
    "Model for a few South Texas ZIP codes (in original Census NAD83)."
    poly = models.PolygonField(srid=4269)


class SouthTexasZipcode(NamedModel):
    "Model for a few South Texas ZIP codes."
    poly = models.PolygonField(srid=32140, null=gisfield_may_be_null)


class Interstate(NamedModel):
    "Geodetic model for U.S. Interstates."
    path = models.LineStringField()


class SouthTexasInterstate(NamedModel):
    "Projected model for South Texas Interstates."
    path = models.LineStringField(srid=32140)
