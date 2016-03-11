from django.utils.encoding import python_2_unicode_compatible

from ..admin import admin
from ..models import models


@python_2_unicode_compatible
class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    class Meta:
        app_label = 'geoadmin'
        required_db_features = ['gis_enabled']

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class CityMercator(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField(srid=3857)

    class Meta:
        required_db_features = ['gis_enabled']

    def __str__(self):
        return self.name

site = admin.AdminSite(name='admin_gis')
site.register(City, admin.OSMGeoAdmin)
site.register(CityMercator, admin.OSMGeoAdmin)
