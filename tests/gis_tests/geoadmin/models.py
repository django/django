from django.contrib.gis.db import models

from ..admin import admin


class Country(models.Model):
    name = models.CharField(max_length=30)

    class Meta:
        app_label = "geoadmin"

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=30)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
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


class CityInline(admin.TabularInline):
    model = City


class CountryAdmin(admin.ModelAdmin):
    inlines = [CityInline]


site = admin.AdminSite(name="gis_admin_modeladmin")
site.register(City, admin.ModelAdmin)

site_gis = admin.AdminSite(name="gis_admin_gismodeladmin")
site_gis.register(City, admin.GISModelAdmin)
site_gis.register(Country, CountryAdmin)

site_gis_custom = admin.AdminSite(name="gis_admin_gismodeladmin")
site_gis_custom.register(City, CityAdminCustomWidgetKwargs)
