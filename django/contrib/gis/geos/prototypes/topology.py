"""
 This module houses the GEOS ctypes prototype functions for the
 topological operations on geometries.
"""
__all__ = ['geos_boundary', 'geos_buffer', 'geos_cascaded_union',
           'geos_centroid', 'geos_convexhull', 'geos_difference',
           'geos_envelope', 'geos_intersection', 'geos_linemerge',
           'geos_pointonsurface', 'geos_preservesimplify', 'geos_simplify',
           'geos_symdifference', 'geos_union', 'geos_relate']

from ctypes import c_double, c_int
from django.contrib.gis.geos.libgeos import geos_version_info, GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_geom, check_minus_one, check_string
from django.contrib.gis.geos.prototypes.geom import geos_char_p
from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc


def topology(func, *args, **kwargs):
    "For GEOS unary topology functions."
    argtypes = [GEOM_PTR]
    if args:
        argtypes += args
    func.argtypes = argtypes
    func.restype = kwargs.get('restype', GEOM_PTR)
    func.errcheck = kwargs.get('errcheck', check_geom)
    return func

### Topology Routines ###
geos_boundary = topology(GEOSFunc('GEOSBoundary'))
geos_buffer = topology(GEOSFunc('GEOSBuffer'), c_double, c_int)
geos_centroid = topology(GEOSFunc('GEOSGetCentroid'))
geos_convexhull = topology(GEOSFunc('GEOSConvexHull'))
geos_difference = topology(GEOSFunc('GEOSDifference'), GEOM_PTR)
geos_envelope = topology(GEOSFunc('GEOSEnvelope'))
geos_intersection = topology(GEOSFunc('GEOSIntersection'), GEOM_PTR)
geos_linemerge = topology(GEOSFunc('GEOSLineMerge'))
geos_pointonsurface = topology(GEOSFunc('GEOSPointOnSurface'))
geos_preservesimplify = topology(GEOSFunc('GEOSTopologyPreserveSimplify'), c_double)
geos_simplify = topology(GEOSFunc('GEOSSimplify'), c_double)
geos_symdifference = topology(GEOSFunc('GEOSSymDifference'), GEOM_PTR)
geos_union = topology(GEOSFunc('GEOSUnion'), GEOM_PTR)

geos_cascaded_union = GEOSFunc('GEOSUnionCascaded')
geos_cascaded_union.argtypes = [GEOM_PTR]
geos_cascaded_union.restype = GEOM_PTR

# GEOSRelate returns a string, not a geometry.
geos_relate = GEOSFunc('GEOSRelate')
geos_relate.argtypes = [GEOM_PTR, GEOM_PTR]
geos_relate.restype = geos_char_p
geos_relate.errcheck = check_string

# Linear referencing routines
info = geos_version_info()
if info['version'] >= '3.2.0':
    geos_project = topology(GEOSFunc('GEOSProject'), GEOM_PTR,
        restype=c_double, errcheck=check_minus_one)
    geos_interpolate = topology(GEOSFunc('GEOSInterpolate'), c_double)

    geos_project_normalized = topology(GEOSFunc('GEOSProjectNormalized'),
        GEOM_PTR, restype=c_double, errcheck=check_minus_one)
    geos_interpolate_normalized = topology(GEOSFunc('GEOSInterpolateNormalized'), c_double)
    __all__.extend(['geos_project', 'geos_interpolate',
        'geos_project_normalized', 'geos_interpolate_normalized'])
