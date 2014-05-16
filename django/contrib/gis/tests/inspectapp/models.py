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

    objects = models.GeoManager()

    class Meta:
        app_label = 'inspectapp'
