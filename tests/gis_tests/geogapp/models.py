from django.utils.encoding import python_2_unicode_compatible

from ..models import models


@python_2_unicode_compatible
class NamedModel(models.Model):
    name = models.CharField(max_length=30)

    objects = models.GeoManager()

    class Meta:
        abstract = True
        required_db_features = ['gis_enabled']

    def __str__(self):
        return self.name


class City(NamedModel):
    point = models.PointField(geography=True)

    class Meta:
        app_label = 'geogapp'
        required_db_features = ['gis_enabled']


class Zipcode(NamedModel):
    code = models.CharField(max_length=10)
    poly = models.PolygonField(geography=True)


class County(NamedModel):
    state = models.CharField(max_length=20)
    mpoly = models.MultiPolygonField(geography=True)

    class Meta:
        app_label = 'geogapp'
        required_db_features = ['gis_enabled']

    def __str__(self):
        return ' County, '.join([self.name, self.state])
