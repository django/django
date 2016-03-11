from django.core.exceptions import ImproperlyConfigured
from django.db import models


class DummyField(models.Field):
    def __init__(self, dim=None, srid=None, geography=None, spatial_index=True, *args, **kwargs):
        super(DummyField, self).__init__(*args, **kwargs)


try:
    from django.contrib.gis.db import models
    # Store a version of the original raster field for testing the exception
    # raised if GDAL isn't installed.
    models.OriginalRasterField = models.RasterField
except ImproperlyConfigured:
    models.GeometryField = DummyField
    models.LineStringField = DummyField
    models.MultiPointField = DummyField
    models.MultiPolygonField = DummyField
    models.PointField = DummyField
    models.PolygonField = DummyField
    models.RasterField = DummyField

try:
    models.RasterField()
except ImproperlyConfigured:
    models.RasterField = DummyField
