"""
 This module houses the GEOS ctypes prototype functions for the
 unary and binary predicate operations on geometries.
"""
from ctypes import c_char, c_char_p, c_double

from django.contrib.gis.geos.libgeos import GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_predicate
from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc


# ## Binary & unary predicate functions ##
def binary_predicate(func, *args):
    "For GEOS binary predicate functions."
    argtypes = [GEOM_PTR, GEOM_PTR]
    if args:
        argtypes += args
    func.argtypes = argtypes
    func.restype = c_char
    func.errcheck = check_predicate
    return func


def unary_predicate(func):
    "For GEOS unary predicate functions."
    func.argtypes = [GEOM_PTR]
    func.restype = c_char
    func.errcheck = check_predicate
    return func

# ## Unary Predicates ##
geos_hasz = unary_predicate(GEOSFunc('GEOSHasZ'))
geos_isempty = unary_predicate(GEOSFunc('GEOSisEmpty'))
geos_isring = unary_predicate(GEOSFunc('GEOSisRing'))
geos_issimple = unary_predicate(GEOSFunc('GEOSisSimple'))
geos_isvalid = unary_predicate(GEOSFunc('GEOSisValid'))

# ## Binary Predicates ##
geos_contains = binary_predicate(GEOSFunc('GEOSContains'))
geos_crosses = binary_predicate(GEOSFunc('GEOSCrosses'))
geos_disjoint = binary_predicate(GEOSFunc('GEOSDisjoint'))
geos_equals = binary_predicate(GEOSFunc('GEOSEquals'))
geos_equalsexact = binary_predicate(GEOSFunc('GEOSEqualsExact'), c_double)
geos_intersects = binary_predicate(GEOSFunc('GEOSIntersects'))
geos_overlaps = binary_predicate(GEOSFunc('GEOSOverlaps'))
geos_relatepattern = binary_predicate(GEOSFunc('GEOSRelatePattern'), c_char_p)
geos_touches = binary_predicate(GEOSFunc('GEOSTouches'))
geos_within = binary_predicate(GEOSFunc('GEOSWithin'))
