from freedom.contrib.gis.db import models
from freedom.contrib.gis import admin
from freedom.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class City(models.Model):
    name = models.CharField(max_length=30)
    point = models.PointField()

    objects = models.GeoManager()

    class Meta:
        app_label = 'geoadmin'

    def __str__(self):
        return self.name

admin.site.register(City, admin.OSMGeoAdmin)
