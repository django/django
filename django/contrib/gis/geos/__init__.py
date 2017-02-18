"""
The GeoDjango GEOS module.  Please consult the GeoDjango documentation
for more details: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geos/
"""
from .collections import GeometryCollection, MultiPoint, MultiLineString, MultiPolygon  # NOQA
from .error import GEOSException, GEOSIndexError  # NOQA
from .factory import fromfile, fromstr  # NOQA
from .geometry import GEOSGeometry, wkt_regex, hex_regex  # NOQA
from .io import WKTReader, WKTWriter, WKBReader, WKBWriter  # NOQA
from .libgeos import geos_version, geos_version_info  # NOQA
from .linestring import LineString, LinearRing  # NOQA
from .point import Point  # NOQA
from .polygon import Polygon  # NOQA

try:
    geos_version_info()
    HAS_GEOS = True
except ImportError:
    HAS_GEOS = False
