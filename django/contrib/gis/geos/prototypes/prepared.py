from ctypes import c_char

from django.contrib.gis.geos.libgeos import (
    GEOM_PTR, PREPGEOM_PTR, geos_version_info,
)
from django.contrib.gis.geos.prototypes.errcheck import check_predicate
from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc

# Prepared geometry constructor and destructors.
geos_prepare = GEOSFunc('GEOSPrepare')
geos_prepare.argtypes = [GEOM_PTR]
geos_prepare.restype = PREPGEOM_PTR

prepared_destroy = GEOSFunc('GEOSPreparedGeom_destroy')
prepared_destroy.argtpes = [PREPGEOM_PTR]
prepared_destroy.restype = None


# Prepared geometry binary predicate support.
def prepared_predicate(func):
    func.argtypes = [PREPGEOM_PTR, GEOM_PTR]
    func.restype = c_char
    func.errcheck = check_predicate
    return func

prepared_contains = prepared_predicate(GEOSFunc('GEOSPreparedContains'))
prepared_contains_properly = prepared_predicate(GEOSFunc('GEOSPreparedContainsProperly'))
prepared_covers = prepared_predicate(GEOSFunc('GEOSPreparedCovers'))
prepared_intersects = prepared_predicate(GEOSFunc('GEOSPreparedIntersects'))

if geos_version_info()['version'] > '3.3.0':
    prepared_crosses = prepared_predicate(GEOSFunc('GEOSPreparedCrosses'))
    prepared_disjoint = prepared_predicate(GEOSFunc('GEOSPreparedDisjoint'))
    prepared_overlaps = prepared_predicate(GEOSFunc('GEOSPreparedOverlaps'))
    prepared_touches = prepared_predicate(GEOSFunc('GEOSPreparedTouches'))
    prepared_within = prepared_predicate(GEOSFunc('GEOSPreparedWithin'))
