from django.contrib.gis.db import models


class AllOGRFields(models.Model):
    f_decimal = models.FloatField()
    f_float = models.FloatField()
    f_int = models.IntegerField()
    f_char = models.CharField(max_length=10)
    f_date = models.DateField()
    f_datetime = models.DateTimeField()
    f_time = models.TimeField()
    geom = models.PolygonField()
    point = models.PointField()


class Fields3D(models.Model):
    point = models.PointField(dim=3)
    pointg = models.PointField(dim=3, geography=True)
    line = models.LineStringField(dim=3)
    poly = models.PolygonField(dim=3)

    class Meta:
        required_db_features = {"supports_3d_storage"}


class Indexes(models.Model):
    point = models.PointField()
    name = models.CharField(max_length=5)
    other = models.IntegerField()

    class Meta:
        required_db_features = {"supports_3d_storage"}
        indexes = [models.Index(fields=["name", "other"], name="name_plus_other")]
