from django.contrib.gis.geos import (
    GEOSException as GeometryException, GEOSGeometry as Geometry,
)

__all__ = ['Geometry', 'GeometryException']
