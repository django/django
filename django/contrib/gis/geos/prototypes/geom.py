from ctypes import c_char_p, c_int, c_size_t, c_ubyte, POINTER
from django.contrib.gis.geos.libgeos import CS_PTR, GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import (
    check_geom, check_minus_one, check_sized_string, check_string, check_zero)
from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc

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

### ctypes generation functions ###
def bin_constructor(func):
    "Generates a prototype for binary construction (HEX, WKB) GEOS routines."
    func.argtypes = [c_char_p, c_size_t]
    func.restype = GEOM_PTR
    func.errcheck = check_geom
    return func

# HEX & WKB output
def bin_output(func):
    "Generates a prototype for the routines that return a a sized string."
    func.argtypes = [GEOM_PTR, POINTER(c_size_t)]
    func.errcheck = check_sized_string
    func.restype = c_uchar_p
    return func

def geom_output(func, argtypes):
    "For GEOS routines that return a geometry."
    if argtypes: func.argtypes = argtypes
    func.restype = GEOM_PTR
    func.errcheck = check_geom
    return func

def geom_index(func):
    "For GEOS routines that return geometries from an index."
    return geom_output(func, [GEOM_PTR, c_int])

def int_from_geom(func, zero=False):
    "Argument is a geometry, return type is an integer."
    func.argtypes = [GEOM_PTR]
    func.restype = c_int
    if zero:
        func.errcheck = check_zero
    else:
        func.errcheck = check_minus_one
    return func

def string_from_geom(func):
    "Argument is a Geometry, return type is a string."
    func.argtypes = [GEOM_PTR]
    func.restype = geos_char_p
    func.errcheck = check_string
    return func

### ctypes prototypes ###

# Deprecated creation routines from WKB, HEX, WKT
from_hex = bin_constructor(GEOSFunc('GEOSGeomFromHEX_buf'))
from_wkb = bin_constructor(GEOSFunc('GEOSGeomFromWKB_buf'))
from_wkt = geom_output(GEOSFunc('GEOSGeomFromWKT'), [c_char_p])

# Deprecated output routines
to_hex = bin_output(GEOSFunc('GEOSGeomToHEX_buf'))
to_wkb = bin_output(GEOSFunc('GEOSGeomToWKB_buf'))
to_wkt = string_from_geom(GEOSFunc('GEOSGeomToWKT'))

# The GEOS geometry type, typeid, num_coordites and number of geometries
geos_normalize = int_from_geom(GEOSFunc('GEOSNormalize'))
geos_type = string_from_geom(GEOSFunc('GEOSGeomType'))
geos_typeid = int_from_geom(GEOSFunc('GEOSGeomTypeId'))
get_dims = int_from_geom(GEOSFunc('GEOSGeom_getDimensions'), zero=True)
get_num_coords = int_from_geom(GEOSFunc('GEOSGetNumCoordinates'))
get_num_geoms = int_from_geom(GEOSFunc('GEOSGetNumGeometries'))

# Geometry creation factories
create_point = geom_output(GEOSFunc('GEOSGeom_createPoint'), [CS_PTR])
create_linestring = geom_output(GEOSFunc('GEOSGeom_createLineString'), [CS_PTR])
create_linearring = geom_output(GEOSFunc('GEOSGeom_createLinearRing'), [CS_PTR])

# Polygon and collection creation routines are special and will not
# have their argument types defined.
create_polygon = geom_output(GEOSFunc('GEOSGeom_createPolygon'), None)
create_collection = geom_output(GEOSFunc('GEOSGeom_createCollection'), None)

# Ring routines
get_extring = geom_output(GEOSFunc('GEOSGetExteriorRing'), [GEOM_PTR])
get_intring = geom_index(GEOSFunc('GEOSGetInteriorRingN'))
get_nrings = int_from_geom(GEOSFunc('GEOSGetNumInteriorRings'))

# Collection Routines
get_geomn = geom_index(GEOSFunc('GEOSGetGeometryN'))

# Cloning
geom_clone = GEOSFunc('GEOSGeom_clone')
geom_clone.argtypes = [GEOM_PTR]
geom_clone.restype = GEOM_PTR

# Destruction routine.
destroy_geom = GEOSFunc('GEOSGeom_destroy')
destroy_geom.argtypes = [GEOM_PTR]
destroy_geom.restype = None

# SRID routines
geos_get_srid = GEOSFunc('GEOSGetSRID')
geos_get_srid.argtypes = [GEOM_PTR]
geos_get_srid.restype = c_int

geos_set_srid = GEOSFunc('GEOSSetSRID')
geos_set_srid.argtypes = [GEOM_PTR, c_int]
geos_set_srid.restype = None
