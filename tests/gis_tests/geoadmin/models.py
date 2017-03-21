from django.contrib.gis.db import models

from ..admin import admin


class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        app_label = 'geoadmin'
        required_db_features = ['gis_enabled']

    def __str__(self):
        return self.name


site = admin.AdminSite(name='admin_gis')
site.register(City, admin.OSMGeoAdmin)
