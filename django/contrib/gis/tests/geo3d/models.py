from django.contrib.gis.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    objects = models.GeoManager()

    class Meta:
        abstract = True
        app_label = 'geo3d'

    def __str__(self):
        return self.name


class City3D(NamedModel):
    point = models.PointField(dim=3)


class Interstate2D(NamedModel):
    line = models.LineStringField(srid=4269)


class Interstate3D(NamedModel):
    line = models.LineStringField(dim=3, srid=4269)


class InterstateProj2D(NamedModel):
    line = models.LineStringField(srid=32140)


class InterstateProj3D(NamedModel):
    line = models.LineStringField(dim=3, srid=32140)


class Polygon2D(NamedModel):
    poly = models.PolygonField(srid=32140)


class Polygon3D(NamedModel):
    poly = models.PolygonField(dim=3, srid=32140)


class SimpleModel(models.Model):

    objects = models.GeoManager()

    class Meta:
        abstract = True
        app_label = 'geo3d'


class Point2D(SimpleModel):
    point = models.PointField()


class Point3D(SimpleModel):
    point = models.PointField(dim=3)


class MultiPoint3D(SimpleModel):
    mpoint = models.MultiPointField(dim=3)
