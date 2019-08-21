"""
 This module houses the GEOS ctypes prototype functions for the
 topological operations on geometries.
"""
from ctypes import c_double, c_int

from django.contrib.gis.geos.libgeos import GEOM_PTR, GEOSFuncFactory
from django.contrib.gis.geos.prototypes.errcheck import (
    check_geom, check_minus_one, check_string,
)
from django.contrib.gis.geos.prototypes.geom import geos_char_p


class Topology(GEOSFuncFactory):
    "For GEOS unary topology functions."
    argtypes = [GEOM_PTR]
    restype = GEOM_PTR
    errcheck = staticmethod(check_geom)


# Topology Routines
geos_boundary = Topology('GEOSBoundary')
geos_buffer = Topology('GEOSBuffer', argtypes=[GEOM_PTR, c_double, c_int])
geos_bufferwithstyle = Topology('GEOSBufferWithStyle', argtypes=[GEOM_PTR, c_double, c_int, c_int, c_int, c_double])
geos_centroid = Topology('GEOSGetCentroid')
geos_convexhull = Topology('GEOSConvexHull')
geos_difference = Topology('GEOSDifference', argtypes=[GEOM_PTR, GEOM_PTR])
geos_envelope = Topology('GEOSEnvelope')
geos_intersection = Topology('GEOSIntersection', argtypes=[GEOM_PTR, GEOM_PTR])
geos_linemerge = Topology('GEOSLineMerge')
geos_pointonsurface = Topology('GEOSPointOnSurface')
geos_preservesimplify = Topology('GEOSTopologyPreserveSimplify', argtypes=[GEOM_PTR, c_double])
geos_simplify = Topology('GEOSSimplify', argtypes=[GEOM_PTR, c_double])
geos_symdifference = Topology('GEOSSymDifference', argtypes=[GEOM_PTR, GEOM_PTR])
geos_union = Topology('GEOSUnion', argtypes=[GEOM_PTR, GEOM_PTR])

geos_unary_union = GEOSFuncFactory('GEOSUnaryUnion', argtypes=[GEOM_PTR], restype=GEOM_PTR)

# GEOSRelate returns a string, not a geometry.
geos_relate = GEOSFuncFactory(
    'GEOSRelate', argtypes=[GEOM_PTR, GEOM_PTR], restype=geos_char_p, errcheck=check_string
)

# Linear referencing routines
geos_project = GEOSFuncFactory(
    'GEOSProject', argtypes=[GEOM_PTR, GEOM_PTR], restype=c_double, errcheck=check_minus_one
)
geos_interpolate = Topology('GEOSInterpolate', argtypes=[GEOM_PTR, c_double])

geos_project_normalized = GEOSFuncFactory(
    'GEOSProjectNormalized', argtypes=[GEOM_PTR, GEOM_PTR], restype=c_double, errcheck=check_minus_one
)
geos_interpolate_normalized = Topology('GEOSInterpolateNormalized', argtypes=[GEOM_PTR, c_double])
