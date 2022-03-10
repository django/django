from django.contrib.gis.db import models
from django.test import ignore_warnings
from django.utils.deprecation import RemovedInDjango50Warning

from ..admin import admin


class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        app_label = "geoadmini_deprecated"

    def __str__(self):
        return self.name


site = admin.AdminSite(name="admin_gis")
with ignore_warnings(category=RemovedInDjango50Warning):
    site.register(City, admin.OSMGeoAdmin)
