from django.contrib.gis.db import models

from ..admin import admin


class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        app_label = "geoadmin"

    def __str__(self):
        return self.name


class CityAdminCustomWidgetKwargs(admin.GISModelAdmin):
    gis_widget_kwargs = {
        "attrs": {
            "default_lat": 55,
            "default_lon": 37,
        },
    }


site = admin.AdminSite(name="gis_admin_modeladmin")
site.register(City, admin.ModelAdmin)

site_gis = admin.AdminSite(name="gis_admin_gismodeladmin")
site_gis.register(City, admin.GISModelAdmin)

site_gis_custom = admin.AdminSite(name="gis_admin_gismodeladmin")
site_gis_custom.register(City, CityAdminCustomWidgetKwargs)
