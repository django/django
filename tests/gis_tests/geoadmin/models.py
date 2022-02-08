from django.contrib.gis.db import models

from ..admin import admin


class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        app_label = "geoadmin"

    def __str__(self):
        return self.name


site = admin.AdminSite(name="gis_admin_modeladmin")
site.register(City, admin.ModelAdmin)

site_gis = admin.AdminSite(name="gis_admin_gismodeladmin")
site_gis.register(City, admin.GISModelAdmin)
