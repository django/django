from ctypes import c_char

from django.contrib.gis.geos.libgeos import (
    GEOM_PTR, PREPGEOM_PTR, GEOSFuncFactory,
)
from django.contrib.gis.geos.prototypes.errcheck import check_predicate

# Prepared geometry constructor and destructors.
geos_prepare = GEOSFuncFactory('GEOSPrepare', argtypes=[GEOM_PTR], restype=PREPGEOM_PTR)
prepared_destroy = GEOSFuncFactory('GEOSPreparedGeom_destroy', argtypes=[PREPGEOM_PTR])


# Prepared geometry binary predicate support.
class PreparedPredicate(GEOSFuncFactory):
    argtypes = [PREPGEOM_PTR, GEOM_PTR]
    restype = c_char
    errcheck = staticmethod(check_predicate)


prepared_contains = PreparedPredicate('GEOSPreparedContains')
prepared_contains_properly = PreparedPredicate('GEOSPreparedContainsProperly')
prepared_covers = PreparedPredicate('GEOSPreparedCovers')
prepared_intersects = PreparedPredicate('GEOSPreparedIntersects')

# Functions added in GEOS 3.3
prepared_crosses = PreparedPredicate('GEOSPreparedCrosses')
prepared_disjoint = PreparedPredicate('GEOSPreparedDisjoint')
prepared_overlaps = PreparedPredicate('GEOSPreparedOverlaps')
prepared_touches = PreparedPredicate('GEOSPreparedTouches')
prepared_within = PreparedPredicate('GEOSPreparedWithin')
