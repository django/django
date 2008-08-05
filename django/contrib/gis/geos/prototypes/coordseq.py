from ctypes import c_double, c_int, c_uint, POINTER
from django.contrib.gis.geos.libgeos import lgeos, GEOM_PTR, CS_PTR
from django.contrib.gis.geos.prototypes.errcheck import last_arg_byref, GEOSException

## Error-checking routines specific to coordinate sequences. ##
def check_cs_ptr(result, func, cargs):
    "Error checking on routines that return Geometries."
    if not result:
        raise GEOSException('Error encountered checking Coordinate Sequence returned from GEOS C function "%s".' % func.__name__)
    return result

def check_cs_op(result, func, cargs):
    "Checks the status code of a coordinate sequence operation."
    if result == 0:
        raise GEOSException('Could not set value on coordinate sequence')
    else:
        return result

def check_cs_get(result, func, cargs):
    "Checking the coordinate sequence retrieval."
    check_cs_op(result, func, cargs)
    # Object in by reference, return its value.
    return last_arg_byref(cargs)

## Coordinate sequence prototype generation functions. ##
def cs_int(func):
    "For coordinate sequence routines that return an integer."
    func.argtypes = [CS_PTR, POINTER(c_uint)]
    func.restype = c_int
    func.errcheck = check_cs_get
    return func

def cs_operation(func, ordinate=False, get=False):
    "For coordinate sequence operations."
    if get:
        # Get routines get double parameter passed-in by reference.
        func.errcheck = check_cs_get
        dbl_param = POINTER(c_double)
    else:
        func.errcheck = check_cs_op
        dbl_param = c_double

    if ordinate:
        # Get/Set ordinate routines have an extra uint parameter.
        func.argtypes = [CS_PTR, c_uint, c_uint, dbl_param]
    else:
        func.argtypes = [CS_PTR, c_uint, dbl_param]

    func.restype = c_int
    return func

def cs_output(func, argtypes):
    "For routines that return a coordinate sequence."
    func.argtypes = argtypes
    func.restype = CS_PTR
    func.errcheck = check_cs_ptr
    return func

## Coordinate Sequence ctypes prototypes ##

# Coordinate Sequence constructors & cloning.
cs_clone = cs_output(lgeos.GEOSCoordSeq_clone, [CS_PTR])
create_cs = cs_output(lgeos.GEOSCoordSeq_create, [c_uint, c_uint])
get_cs = cs_output(lgeos.GEOSGeom_getCoordSeq, [GEOM_PTR])

# Getting, setting ordinate
cs_getordinate = cs_operation(lgeos.GEOSCoordSeq_getOrdinate, ordinate=True, get=True)
cs_setordinate = cs_operation(lgeos.GEOSCoordSeq_setOrdinate, ordinate=True)

# For getting, x, y, z
cs_getx = cs_operation(lgeos.GEOSCoordSeq_getX, get=True)
cs_gety = cs_operation(lgeos.GEOSCoordSeq_getY, get=True)
cs_getz = cs_operation(lgeos.GEOSCoordSeq_getZ, get=True)

# For setting, x, y, z
cs_setx = cs_operation(lgeos.GEOSCoordSeq_setX)
cs_sety = cs_operation(lgeos.GEOSCoordSeq_setY)
cs_setz = cs_operation(lgeos.GEOSCoordSeq_setZ)

# These routines return size & dimensions.
cs_getsize = cs_int(lgeos.GEOSCoordSeq_getSize)
cs_getdims = cs_int(lgeos.GEOSCoordSeq_getDimensions)
