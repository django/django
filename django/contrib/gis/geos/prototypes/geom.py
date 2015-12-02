from ctypes import POINTER, c_char_p, c_int, c_size_t, c_ubyte

from django.contrib.gis.geos.libgeos import CS_PTR, GEOM_PTR, GEOSFuncFactory
from django.contrib.gis.geos.prototypes.errcheck import (
    check_geom, check_minus_one, check_sized_string, check_string, check_zero,
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
class BinConstructor(GEOSFuncFactory):
    "Generates a prototype for binary construction (HEX, WKB) GEOS routines."
    argtypes = [c_char_p, c_size_t]
    restype = GEOM_PTR
    errcheck = staticmethod(check_geom)


# HEX & WKB output
class BinOutput(GEOSFuncFactory):
    "Generates a prototype for the routines that return a sized string."
    argtypes = [GEOM_PTR, POINTER(c_size_t)]
    restype = c_uchar_p
    errcheck = staticmethod(check_sized_string)


class GeomOutput(GEOSFuncFactory):
    "For GEOS routines that return a geometry."
    restype = GEOM_PTR
    errcheck = staticmethod(check_geom)

    def get_func(self, argtypes):
        self.argtypes = argtypes
        return super(GeomOutput, self).get_func()


class IntFromGeom(GEOSFuncFactory):
    "Argument is a geometry, return type is an integer."
    argtypes = [GEOM_PTR]
    restype = c_int

    def get_func(self, zero=False):
        if zero:
            self.errcheck = check_zero
        else:
            self.errcheck = check_minus_one
        return super(IntFromGeom, self).get_func()


class StringFromGeom(GEOSFuncFactory):
    "Argument is a Geometry, return type is a string."
    argtypes = [GEOM_PTR]
    restype = geos_char_p
    errcheck = staticmethod(check_string)


# ### ctypes prototypes ###

# Deprecated creation routines from WKB, HEX, WKT
from_hex = BinConstructor('GEOSGeomFromHEX_buf')
from_wkb = BinConstructor('GEOSGeomFromWKB_buf')
from_wkt = GeomOutput('GEOSGeomFromWKT', [c_char_p])

# Deprecated output routines
to_hex = BinOutput('GEOSGeomToHEX_buf')
to_wkb = BinOutput('GEOSGeomToWKB_buf')
to_wkt = StringFromGeom('GEOSGeomToWKT')

# The GEOS geometry type, typeid, num_coordinates and number of geometries
geos_normalize = IntFromGeom('GEOSNormalize')
geos_type = StringFromGeom('GEOSGeomType')
geos_typeid = IntFromGeom('GEOSGeomTypeId')
get_dims = IntFromGeom('GEOSGeom_getDimensions', zero=True)
get_num_coords = IntFromGeom('GEOSGetNumCoordinates')
get_num_geoms = IntFromGeom('GEOSGetNumGeometries')

# Geometry creation factories
create_point = GeomOutput('GEOSGeom_createPoint', [CS_PTR])
create_linestring = GeomOutput('GEOSGeom_createLineString', [CS_PTR])
create_linearring = GeomOutput('GEOSGeom_createLinearRing', [CS_PTR])

# Polygon and collection creation routines are special and will not
# have their argument types defined.
create_polygon = GeomOutput('GEOSGeom_createPolygon', None)
create_collection = GeomOutput('GEOSGeom_createCollection', None)

# Ring routines
get_extring = GeomOutput('GEOSGetExteriorRing', [GEOM_PTR])
get_intring = GeomOutput('GEOSGetInteriorRingN', [GEOM_PTR, c_int])
get_nrings = IntFromGeom('GEOSGetNumInteriorRings')

# Collection Routines
get_geomn = GeomOutput('GEOSGetGeometryN', [GEOM_PTR, c_int])

# Cloning
geom_clone = GEOSFuncFactory('GEOSGeom_clone', argtypes=[GEOM_PTR], restype=GEOM_PTR)

# Destruction routine.
destroy_geom = GEOSFuncFactory('GEOSGeom_destroy', argtypes=[GEOM_PTR])

# SRID routines
geos_get_srid = GEOSFuncFactory('GEOSGetSRID', argtypes=[GEOM_PTR], restype=c_int)
geos_set_srid = GEOSFuncFactory('GEOSSetSRID', argtypes=[GEOM_PTR, c_int])
