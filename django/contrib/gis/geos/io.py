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
        "Return a GEOSGeometry for the given WKB buffer."
        return GEOSGeometry(super().read(wkb))


class WKTReader(_WKTReader):
    def read(self, wkt):
        "Return a GEOSGeometry for the given WKT string."
        return GEOSGeometry(super().read(wkt))
