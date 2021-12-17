from django.contrib.gis.db import models

from ..admin import admin


class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        app_label = 'geoadmin'

    def __str__(self):
        return self.name


class CityAdmin(admin.GISModelAdmin):
    gis_widget_kwargs = {
        'default_lat': 55,
        'default_lon': 37,
        'default_zoom': 12
    }

class CityDefaultAdmin(admin.GISModelAdmin):
    pass


site = admin.AdminSite(name='gis_admin_modeladmin')
site.register(City, admin.ModelAdmin)

site_gis = admin.AdminSite(name='gis_admin_gismodeladmin')
site_gis.register(City, CityAdmin)

site_gis_default = admin.AdminSite(name='gis_admin_gismodeladmin')
site_gis_default.register(City, CityDefaultAdmin)
