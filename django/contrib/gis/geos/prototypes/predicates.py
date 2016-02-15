"""
 This module houses the GEOS ctypes prototype functions for the
 unary and binary predicate operations on geometries.
"""
from ctypes import c_char, c_char_p, c_double

from django.contrib.gis.geos.libgeos import GEOM_PTR, GEOSFuncFactory
from django.contrib.gis.geos.prototypes.errcheck import check_predicate


# ## Binary & unary predicate factories ##
class UnaryPredicate(GEOSFuncFactory):
    "For GEOS unary predicate functions."
    argtypes = [GEOM_PTR]
    restype = c_char
    errcheck = staticmethod(check_predicate)


class BinaryPredicate(UnaryPredicate):
    "For GEOS binary predicate functions."
    argtypes = [GEOM_PTR, GEOM_PTR]


# ## Unary Predicates ##
geos_hasz = UnaryPredicate('GEOSHasZ')
geos_isclosed = UnaryPredicate('GEOSisClosed')
geos_isempty = UnaryPredicate('GEOSisEmpty')
geos_isring = UnaryPredicate('GEOSisRing')
geos_issimple = UnaryPredicate('GEOSisSimple')
geos_isvalid = UnaryPredicate('GEOSisValid')

# ## Binary Predicates ##
geos_contains = BinaryPredicate('GEOSContains')
geos_covers = BinaryPredicate('GEOSCovers')
geos_crosses = BinaryPredicate('GEOSCrosses')
geos_disjoint = BinaryPredicate('GEOSDisjoint')
geos_equals = BinaryPredicate('GEOSEquals')
geos_equalsexact = BinaryPredicate('GEOSEqualsExact', argtypes=[GEOM_PTR, GEOM_PTR, c_double])
geos_intersects = BinaryPredicate('GEOSIntersects')
geos_overlaps = BinaryPredicate('GEOSOverlaps')
geos_relatepattern = BinaryPredicate('GEOSRelatePattern', argtypes=[GEOM_PTR, GEOM_PTR, c_char_p])
geos_touches = BinaryPredicate('GEOSTouches')
geos_within = BinaryPredicate('GEOSWithin')
