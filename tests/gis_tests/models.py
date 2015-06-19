from django.core.exceptions import ImproperlyConfigured
from django.db import models


class DummyField(models.Field):
    def __init__(self, dim=None, srid=None, geography=None, spatial_index=True, *args, **kwargs):
        super(DummyField, self).__init__(*args, **kwargs)

try:
    from django.contrib.gis.db import models
    try:
        models.RasterField()
    except ImproperlyConfigured:
        models.RasterField = DummyField
except ImproperlyConfigured:
    models.GeoManager = models.Manager
    models.GeometryField = DummyField
    models.LineStringField = DummyField
    models.MultiPointField = DummyField
    models.MultiPolygonField = DummyField
    models.PointField = DummyField
    models.PolygonField = DummyField
    models.RasterField = DummyField
