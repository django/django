from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models
except ImproperlyConfigured:
    from django.db import models

    class DummyField(models.Field):
        def __init__(self, dim=None, srid=None, geography=None, *args, **kwargs):
            super(DummyField, self).__init__(*args, **kwargs)

    models.GeoManager = models.Manager
    models.GeometryField = DummyField
    models.LineStringField = DummyField
    models.MultiPointField = DummyField
    models.MultiPolygonField = DummyField
    models.PointField = DummyField
    models.PolygonField = DummyField
