"""
 This module is for the miscellaneous GEOS routines, particularly the
 ones that return the area, distance, and length.
"""
from ctypes import POINTER, c_double, c_int

from django.contrib.gis.geos.libgeos import GEOM_PTR, GEOSFuncFactory
from django.contrib.gis.geos.prototypes.errcheck import check_dbl, check_string
from django.contrib.gis.geos.prototypes.geom import geos_char_p

__all__ = ['geos_area', 'geos_distance', 'geos_length', 'geos_isvalidreason']


class DblFromGeom(GEOSFuncFactory):
    """
    Argument is a Geometry, return type is double that is passed
    in by reference as the last argument.
    """
    restype = c_int  # Status code returned
    errcheck = staticmethod(check_dbl)


# ### ctypes prototypes ###

# Area, distance, and length prototypes.
geos_area = DblFromGeom('GEOSArea', argtypes=[GEOM_PTR, POINTER(c_double)])
geos_distance = DblFromGeom('GEOSDistance', argtypes=[GEOM_PTR, GEOM_PTR, POINTER(c_double)])
geos_length = DblFromGeom('GEOSLength', argtypes=[GEOM_PTR, POINTER(c_double)])
geos_isvalidreason = GEOSFuncFactory(
    'GEOSisValidReason', restype=geos_char_p, errcheck=check_string, argtypes=[GEOM_PTR]
)
