from ctypes import c_char
from django.contrib.gis.geos.libgeos import lgeos, GEOM_PTR, PREPGEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_predicate

# Prepared geometry constructor and destructors.
geos_prepare = lgeos.GEOSPrepare
geos_prepare.argtypes = [GEOM_PTR]
geos_prepare.restype = PREPGEOM_PTR

prepared_destroy = lgeos.GEOSPreparedGeom_destroy
prepared_destroy.argtpes = [PREPGEOM_PTR]
prepared_destroy.restype = None

# Prepared geometry binary predicate support.
def prepared_predicate(func):
    func.argtypes= [PREPGEOM_PTR, GEOM_PTR]
    func.restype = c_char
    func.errcheck = check_predicate
    return func

prepared_contains = prepared_predicate(lgeos.GEOSPreparedContains)
prepared_contains_properly = prepared_predicate(lgeos.GEOSPreparedContainsProperly)
prepared_covers = prepared_predicate(lgeos.GEOSPreparedCovers)
prepared_intersects = prepared_predicate(lgeos.GEOSPreparedIntersects)
