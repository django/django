"""
The GeoDjango GEOS module.  Please consult the GeoDjango documentation
for more details: 
  http://geodjango.org/docs/geos.html
"""
try:
    from .libgeos import geos_version, geos_version_info, GEOS_PREPARE
    HAS_GEOS = True
except ImportError:
    HAS_GEOS = False

if HAS_GEOS:
    from .geometry import GEOSGeometry, wkt_regex, hex_regex
    from .point import Point
    from .linestring import LineString, LinearRing
    from .polygon import Polygon
    from .collections import GeometryCollection, MultiPoint, MultiLineString, MultiPolygon
    from .error import GEOSException, GEOSIndexError
    from .io import WKTReader, WKTWriter, WKBReader, WKBWriter
    from .factory import fromfile, fromstr
