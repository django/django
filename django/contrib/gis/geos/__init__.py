"""
The GeoDjango GEOS module.  Please consult the GeoDjango documentation
for more details: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geos/
"""
__all__ = ['HAS_GEOS']

try:
    from .libgeos import geos_version, geos_version_info  # NOQA: flake8 detects only the last __all__
    HAS_GEOS = True
    __all__ += ['geos_version', 'geos_version_info']
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

    __all__ += [
        'GEOSGeometry', 'wkt_regex', 'hex_regex', 'Point', 'LineString',
        'LinearRing', 'Polygon', 'GeometryCollection', 'MultiPoint',
        'MultiLineString', 'MultiPolygon', 'GEOSException', 'GEOSIndexError',
        'WKTReader', 'WKTWriter', 'WKBReader', 'WKBWriter', 'fromfile',
        'fromstr',
    ]
