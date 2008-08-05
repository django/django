"""
 This module is for the miscellaneous GEOS routines, particularly the
 ones that return the area, distance, and length.
"""
from ctypes import c_int, c_double, POINTER
from django.contrib.gis.geos.libgeos import lgeos, GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_dbl

### ctypes generator function ###
def dbl_from_geom(func, num_geom=1):
    """
    Argument is a Geometry, return type is double that is passed
    in by reference as the last argument.
    """
    argtypes = [GEOM_PTR for i in xrange(num_geom)]
    argtypes += [POINTER(c_double)]
    func.argtypes = argtypes
    func.restype = c_int # Status code returned
    func.errcheck = check_dbl
    return func

### ctypes prototypes ###

# Area, distance, and length prototypes.
geos_area = dbl_from_geom(lgeos.GEOSArea)
geos_distance = dbl_from_geom(lgeos.GEOSDistance, num_geom=2)
geos_length = dbl_from_geom(lgeos.GEOSLength)
