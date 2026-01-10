from ctypes import POINTER, c_byte, c_double, c_int, c_uint
from functools import partial

from django.contrib.gis.geos.libgeos import (
    CS_PTR,
    GEOM_PTR,
    GEOSFuncFactory,
)
from django.contrib.gis.geos.prototypes.errcheck import (
    GEOSException,
    check_predicate,
    last_arg_byref,
)


# ## Error-checking routines specific to coordinate sequences. ##
def check_cs_op(result, func, cargs):
    "Check the status code of a coordinate sequence operation."
    if result == 0:
        raise GEOSException("Could not set value on coordinate sequence")
    else:
        return result


def check_cs_get(result, func, cargs, num_ordinates=1):
    "Check the coordinate sequence retrieval."
    check_cs_op(result, func, cargs)
    # Object in by reference, return its value.
    if num_ordinates == 1:
        return last_arg_byref(cargs)
    return tuple(cargs[-num_ordinates + i]._obj.value for i in range(num_ordinates))


# ## Coordinate sequence prototype factory classes. ##
class CsInt(GEOSFuncFactory):
    "For coordinate sequence routines that return an integer."

    argtypes = [CS_PTR, POINTER(c_uint)]
    restype = c_int
    errcheck = staticmethod(check_cs_get)


class CsOperation(GEOSFuncFactory):
    "For coordinate sequence operations."

    restype = c_int

    def __init__(self, *args, ordinate=False, get=False, num_ordinates=1, **kwargs):
        if get:
            # Get routines have double parameter passed-in by reference.
            errcheck = partial(check_cs_get, num_ordinates=num_ordinates)
            dbl_param = POINTER(c_double)
        else:
            errcheck = check_cs_op
            dbl_param = c_double

        if ordinate:
            # Get/Set ordinate routines have an extra uint parameter.
            argtypes = [CS_PTR, c_uint, c_uint] + [dbl_param] * num_ordinates
        else:
            argtypes = [CS_PTR, c_uint] + [dbl_param] * num_ordinates

        super().__init__(
            *args, **{**kwargs, "errcheck": errcheck, "argtypes": argtypes}
        )


class CsOutput(GEOSFuncFactory):
    restype = CS_PTR

    @staticmethod
    def errcheck(result, func, cargs):
        if not result:
            raise GEOSException(
                "Error encountered checking Coordinate Sequence returned from GEOS "
                'C function "%s".' % func.__name__
            )
        return result


class CsUnaryPredicate(GEOSFuncFactory):
    argtypes = [CS_PTR]
    restype = c_byte
    errcheck = staticmethod(check_predicate)


# ## Coordinate Sequence ctypes prototypes ##

# Coordinate Sequence constructors & cloning.
cs_clone = CsOutput("GEOSCoordSeq_clone", argtypes=[CS_PTR])
create_cs = CsOutput("GEOSCoordSeq_create", argtypes=[c_uint, c_uint])
get_cs = CsOutput("GEOSGeom_getCoordSeq", argtypes=[GEOM_PTR])

# Getting, setting ordinate
cs_getordinate = CsOperation("GEOSCoordSeq_getOrdinate", ordinate=True, get=True)
cs_setordinate = CsOperation("GEOSCoordSeq_setOrdinate", ordinate=True)

# For getting, x, y, z, m
cs_getm = CsOperation("GEOSCoordSeq_getM", get=True)
cs_getxy = CsOperation("GEOSCoordSeq_getXY", get=True, num_ordinates=2)
cs_getxyz = CsOperation("GEOSCoordSeq_getXYZ", get=True, num_ordinates=3)

# For setting, x, y, z, m
cs_setm = CsOperation("GEOSCoordSeq_setM")
cs_setxy = CsOperation("GEOSCoordSeq_setXY", num_ordinates=2)
cs_setxyz = CsOperation("GEOSCoordSeq_setXYZ", num_ordinates=3)

# These routines return size & dimensions.
cs_getsize = CsInt("GEOSCoordSeq_getSize")
cs_getdims = CsInt("GEOSCoordSeq_getDimensions")

# Unary Predicates
cs_hasm = CsUnaryPredicate("GEOSCoordSeq_hasM")

cs_is_ccw = GEOSFuncFactory(
    "GEOSCoordSeq_isCCW", restype=c_int, argtypes=[CS_PTR, POINTER(c_byte)]
)
