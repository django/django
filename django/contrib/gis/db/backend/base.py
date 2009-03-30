"""
 This module holds the base `SpatialBackend` object, which is
 instantiated by each spatial backend with the features it has.
"""
# TODO: Create a `Geometry` protocol and allow user to use
# different Geometry objects -- for now we just use GEOSGeometry.
from django.contrib.gis.geos import GEOSGeometry, GEOSException

class BaseSpatialBackend(object):
    Geometry = GEOSGeometry
    GeometryException = GEOSException

    def __init__(self, **kwargs):
        kwargs.setdefault('distance_functions', {})
        kwargs.setdefault('limited_where', {})
        for k, v in kwargs.iteritems(): setattr(self, k, v)
 
    def __getattr__(self, name):
        """
        All attributes of the spatial backend return False by default.
        """
        try:
            return self.__dict__[name]
        except KeyError:
            return False

