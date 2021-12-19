from ctypes import POINTER, c_char_p, c_int, c_ubyte, c_uint

from django.contrib.gis.geos.libgeos import CS_PTR, GEOM_PTR, GEOSFuncFactory
from django.contrib.gis.geos.prototypes.errcheck import (
    check_geom, check_minus_one, check_string,
)

# This is the return type used by binary output (WKB, HEX) routines.
c_uchar_p = POINTER(c_ubyte)


# We create a simple subclass of c_char_p here because when the response
# type is set to c_char_p, you get a _Python_ string and there's no way
# to access the string's address inside the error checking function.
# In other words, you can't free the memory allocated inside GEOS.  Previously,
# the return type would just be omitted and the integer address would be
# used -- but this allows us to be specific in the function definition and
# keeps the reference so it may be free'd.
class geos_char_p(c_char_p):
    pass


# ### ctypes factory classes ###
class GeomOutput(GEOSFuncFactory):
    "For GEOS routines that return a geometry."
    restype = GEOM_PTR
    errcheck = staticmethod(check_geom)


class IntFromGeom(GEOSFuncFactory):
    "Argument is a geometry, return type is an integer."
    argtypes = [GEOM_PTR]
    restype = c_int
    errcheck = staticmethod(check_minus_one)


class StringFromGeom(GEOSFuncFactory):
    "Argument is a Geometry, return type is a string."
    argtypes = [GEOM_PTR]
    restype = geos_char_p
    errcheck = staticmethod(check_string)


# ### ctypes prototypes ###

# The GEOS geometry type, typeid, num_coordinates and number of geometries
geos_normalize = IntFromGeom('GEOSNormalize')
geos_type = StringFromGeom('GEOSGeomType')
geos_typeid = IntFromGeom('GEOSGeomTypeId')
get_dims = GEOSFuncFactory('GEOSGeom_getDimensions', argtypes=[GEOM_PTR], restype=c_int)
get_num_coords = IntFromGeom('GEOSGetNumCoordinates')
get_num_geoms = IntFromGeom('GEOSGetNumGeometries')

# Geometry creation factories
create_point = GeomOutput('GEOSGeom_createPoint', argtypes=[CS_PTR])
create_linestring = GeomOutput('GEOSGeom_createLineString', argtypes=[CS_PTR])
create_linearring = GeomOutput('GEOSGeom_createLinearRing', argtypes=[CS_PTR])

# Polygon and collection creation routines need argument types defined
# for compatibility with some platforms, e.g. macOS ARM64. With argtypes
# defined, arrays are automatically cast and byref() calls are not needed.
create_polygon = GeomOutput(
    'GEOSGeom_createPolygon', argtypes=[GEOM_PTR, POINTER(GEOM_PTR), c_uint],
)
create_empty_polygon = GeomOutput('GEOSGeom_createEmptyPolygon', argtypes=[])
create_collection = GeomOutput(
    'GEOSGeom_createCollection', argtypes=[c_int, POINTER(GEOM_PTR), c_uint],
)

# Ring routines
get_extring = GeomOutput('GEOSGetExteriorRing', argtypes=[GEOM_PTR])
get_intring = GeomOutput('GEOSGetInteriorRingN', argtypes=[GEOM_PTR, c_int])
get_nrings = IntFromGeom('GEOSGetNumInteriorRings')

# Collection Routines
get_geomn = GeomOutput('GEOSGetGeometryN', argtypes=[GEOM_PTR, c_int])

# Cloning
geom_clone = GEOSFuncFactory('GEOSGeom_clone', argtypes=[GEOM_PTR], restype=GEOM_PTR)

# Destruction routine.
destroy_geom = GEOSFuncFactory('GEOSGeom_destroy', argtypes=[GEOM_PTR])

# SRID routines
geos_get_srid = GEOSFuncFactory('GEOSGetSRID', argtypes=[GEOM_PTR], restype=c_int)
geos_set_srid = GEOSFuncFactory('GEOSSetSRID', argtypes=[GEOM_PTR, c_int])
