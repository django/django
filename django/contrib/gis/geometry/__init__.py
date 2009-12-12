from django.conf import settings

__all__ = ['Geometry', 'GeometryException']

from django.contrib.gis.geos import GEOSGeometry, GEOSException

Geometry = GEOSGeometry
GeometryException = GEOSException

