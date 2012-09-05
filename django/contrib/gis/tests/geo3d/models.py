from django.contrib.gis.db import models
from django.utils.encoding import python_2_unicode_compatible

@python_2_unicode_compatible
class City3D(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField(dim=3)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Interstate2D(models.Model):
    name = models.CharField(max_length=30)
    line = models.LineStringField(srid=4269)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Interstate3D(models.Model):
    name = models.CharField(max_length=30)
    line = models.LineStringField(dim=3, srid=4269)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class InterstateProj2D(models.Model):
    name = models.CharField(max_length=30)
    line = models.LineStringField(srid=32140)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class InterstateProj3D(models.Model):
    name = models.CharField(max_length=30)
    line = models.LineStringField(dim=3, srid=32140)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Polygon2D(models.Model):
    name = models.CharField(max_length=30)
    poly = models.PolygonField(srid=32140)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Polygon3D(models.Model):
    name = models.CharField(max_length=30)
    poly = models.PolygonField(dim=3, srid=32140)
    objects = models.GeoManager()

    def __str__(self):
        return self.name

class Point2D(models.Model):
    point = models.PointField()
    objects = models.GeoManager()

class Point3D(models.Model):
    point = models.PointField(dim=3)
    objects = models.GeoManager()

class MultiPoint3D(models.Model):
    mpoint = models.MultiPointField(dim=3)
    objects = models.GeoManager()
