"""
Module that holds classes for performing I/O operations on GEOS geometry
objects.  Specifically, this has Python implementations of WKB/WKT
reader and writer classes.
"""
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.prototypes.io import (
    WKBWriter, WKTWriter, _WKBReader, _WKTReader,
)

__all__ = ['WKBWriter', 'WKTWriter', 'WKBReader', 'WKTReader']


# Public classes for (WKB|WKT)Reader, which return GEOSGeometry
class WKBReader(_WKBReader):
    def read(self, wkb):
        "Returns a GEOSGeometry for the given WKB buffer."
        return GEOSGeometry(super(WKBReader, self).read(wkb))


class WKTReader(_WKTReader):
    def read(self, wkt):
        "Returns a GEOSGeometry for the given WKT string."
        return GEOSGeometry(super(WKTReader, self).read(wkt))
