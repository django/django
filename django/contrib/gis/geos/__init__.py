"""
The GeoDjango GEOS module.  Please consult the GeoDjango documentation
for more details: 
  http://geodjango.org/docs/geos.html
"""
from django.contrib.gis.geos.geometry import GEOSGeometry, wkt_regex, hex_regex
from django.contrib.gis.geos.point import Point
from django.contrib.gis.geos.linestring import LineString, LinearRing
from django.contrib.gis.geos.polygon import Polygon
from django.contrib.gis.geos.collections import GeometryCollection, MultiPoint, MultiLineString, MultiPolygon
from django.contrib.gis.geos.error import GEOSException, GEOSIndexError
from django.contrib.gis.geos.io import WKTReader, WKTWriter, WKBReader, WKBWriter
from django.contrib.gis.geos.factory import fromfile, fromstr
from django.contrib.gis.geos.libgeos import geos_version, geos_version_info, GEOS_PREPARE
