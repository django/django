from django.contrib.gis.db import models


class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class City3D(NamedModel):
    point = models.PointField(dim=3)
    pointg = models.PointField(dim=3, geography=True)

    class Meta:
        required_db_features = {'supports_3d_storage'}


class Interstate2D(NamedModel):
    line = models.LineStringField(srid=4269)


class Interstate3D(NamedModel):
    line = models.LineStringField(dim=3, srid=4269)

    class Meta:
        required_db_features = {'supports_3d_storage'}


class InterstateProj2D(NamedModel):
    line = models.LineStringField(srid=32140)


class InterstateProj3D(NamedModel):
    line = models.LineStringField(dim=3, srid=32140)

    class Meta:
        required_db_features = {'supports_3d_storage'}


class Polygon2D(NamedModel):
    poly = models.PolygonField(srid=32140)


class Polygon3D(NamedModel):
    poly = models.PolygonField(dim=3, srid=32140)

    class Meta:
        required_db_features = {'supports_3d_storage'}


class SimpleModel(models.Model):

    class Meta:
        abstract = True


class Point2D(SimpleModel):
    point = models.PointField()


class Point3D(SimpleModel):
    point = models.PointField(dim=3)

    class Meta:
        required_db_features = {'supports_3d_storage'}


class MultiPoint3D(SimpleModel):
    mpoint = models.MultiPointField(dim=3)

    class Meta:
        required_db_features = {'supports_3d_storage'}
