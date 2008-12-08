from ctypes import c_char_p, c_int, c_size_t, c_ubyte, c_uint, POINTER
from django.contrib.gis.geos.libgeos import lgeos, CS_PTR, GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import \
    check_geom, check_minus_one, check_sized_string, check_string, check_zero

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
    # We do _not_ specify an argument type because we want just an
    # address returned from the function.
    func.argtypes = [GEOM_PTR]
    func.restype = geos_char_p
    func.errcheck = check_string
    return func

### ctypes prototypes ###

# TODO: Tell all users to use GEOS 3.0.0, instead of the release 
#  candidates, and use the new Reader and Writer APIs (e.g.,
#  GEOSWKT[Reader|Writer], GEOSWKB[Reader|Writer]).  A good time
#  to do this will be when Refractions releases a Windows PostGIS
#  installer using GEOS 3.0.0.

# Creation routines from WKB, HEX, WKT
from_hex = bin_constructor(lgeos.GEOSGeomFromHEX_buf)
from_wkb = bin_constructor(lgeos.GEOSGeomFromWKB_buf)
from_wkt = geom_output(lgeos.GEOSGeomFromWKT, [c_char_p])

# Output routines
to_hex = bin_output(lgeos.GEOSGeomToHEX_buf)
to_wkb = bin_output(lgeos.GEOSGeomToWKB_buf)
to_wkt = string_from_geom(lgeos.GEOSGeomToWKT)

# The GEOS geometry type, typeid, num_coordites and number of geometries
geos_normalize = int_from_geom(lgeos.GEOSNormalize)
geos_type = string_from_geom(lgeos.GEOSGeomType)
geos_typeid = int_from_geom(lgeos.GEOSGeomTypeId)
get_dims = int_from_geom(lgeos.GEOSGeom_getDimensions, zero=True)
get_num_coords = int_from_geom(lgeos.GEOSGetNumCoordinates)
get_num_geoms = int_from_geom(lgeos.GEOSGetNumGeometries)

# Geometry creation factories
create_point = geom_output(lgeos.GEOSGeom_createPoint, [CS_PTR])
create_linestring = geom_output(lgeos.GEOSGeom_createLineString, [CS_PTR]) 
create_linearring = geom_output(lgeos.GEOSGeom_createLinearRing, [CS_PTR])

# Polygon and collection creation routines are special and will not
# have their argument types defined.
create_polygon = geom_output(lgeos.GEOSGeom_createPolygon, None)
create_collection = geom_output(lgeos.GEOSGeom_createCollection, None)

# Ring routines
get_extring = geom_output(lgeos.GEOSGetExteriorRing, [GEOM_PTR])
get_intring = geom_index(lgeos.GEOSGetInteriorRingN)
get_nrings = int_from_geom(lgeos.GEOSGetNumInteriorRings)

# Collection Routines
get_geomn = geom_index(lgeos.GEOSGetGeometryN)

# Cloning
geom_clone = lgeos.GEOSGeom_clone
geom_clone.argtypes = [GEOM_PTR]
geom_clone.restype = GEOM_PTR

# Destruction routine.
destroy_geom = lgeos.GEOSGeom_destroy
destroy_geom.argtypes = [GEOM_PTR]
destroy_geom.restype = None

# SRID routines
geos_get_srid = lgeos.GEOSGetSRID
geos_get_srid.argtypes = [GEOM_PTR]
geos_get_srid.restype = c_int

geos_set_srid = lgeos.GEOSSetSRID
geos_set_srid.argtypes = [GEOM_PTR, c_int]
geos_set_srid.restype = None
