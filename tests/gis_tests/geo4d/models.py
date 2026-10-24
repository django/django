from django.contrib.gis.db import models

from ..geo3d.models import NamedModel, SimpleModel


class City4D(NamedModel):
    point = models.PointField(dim=4)
    pointg = models.PointField(dim=4, geography=True)

    class Meta:
        required_db_features = {"supports_4d_storage"}


class Interstate4D(NamedModel):
    line = models.LineStringField(dim=4, srid=4269)

    class Meta:
        required_db_features = {"supports_4d_storage"}


class InterstateProj4D(NamedModel):
    line = models.LineStringField(dim=4, srid=32140)

    class Meta:
        required_db_features = {"supports_4d_storage"}


class Polygon4D(NamedModel):
    poly = models.PolygonField(dim=4, srid=32140)

    class Meta:
        required_db_features = {"supports_4d_storage"}


class Point4D(SimpleModel):
    point = models.PointField(dim=4)

    class Meta:
        required_db_features = {"supports_4d_storage"}


class MultiPoint4D(SimpleModel):
    mpoint = models.MultiPointField(dim=4)

    class Meta:
        required_db_features = {"supports_4d_storage"}
