"""
 This module houses the GEOS ctypes prototype functions for the 
 unary and binary predicate operations on geometries.
"""
from ctypes import c_char, c_char_p, c_double
from django.contrib.gis.geos.libgeos import lgeos, GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_predicate

## Binary & unary predicate functions ##
def binary_predicate(func, *args):
    "For GEOS binary predicate functions."
    argtypes = [GEOM_PTR, GEOM_PTR]
    if args: argtypes += args
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

## Unary Predicates ##
geos_hasz = unary_predicate(lgeos.GEOSHasZ)
geos_isempty = unary_predicate(lgeos.GEOSisEmpty)
geos_isring = unary_predicate(lgeos.GEOSisRing)
geos_issimple = unary_predicate(lgeos.GEOSisSimple)
geos_isvalid = unary_predicate(lgeos.GEOSisValid)

## Binary Predicates ##
geos_contains = binary_predicate(lgeos.GEOSContains)
geos_crosses = binary_predicate(lgeos.GEOSCrosses)
geos_disjoint = binary_predicate(lgeos.GEOSDisjoint)
geos_equals = binary_predicate(lgeos.GEOSEquals)
geos_equalsexact = binary_predicate(lgeos.GEOSEqualsExact, c_double)
geos_intersects = binary_predicate(lgeos.GEOSIntersects)
geos_overlaps = binary_predicate(lgeos.GEOSOverlaps)
geos_relatepattern = binary_predicate(lgeos.GEOSRelatePattern, c_char_p)
geos_touches = binary_predicate(lgeos.GEOSTouches)
geos_within = binary_predicate(lgeos.GEOSWithin)
