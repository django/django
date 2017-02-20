"""
 This module houses the error-checking routines used by the GDAL
 ctypes prototypes.
"""
from ctypes import c_void_p, string_at

from django.contrib.gis.gdal.error import (
    GDALException, SRSException, check_err,
)
from django.contrib.gis.gdal.libgdal import lgdal


# Helper routines for retrieving pointers and/or values from
# arguments passed in by reference.
def arg_byref(args, offset=-1):
    "Return the pointer argument's by-reference value."
    return args[offset]._obj.value


def ptr_byref(args, offset=-1):
    "Return the pointer argument passed in by-reference."
    return args[offset]._obj


# ### String checking Routines ###
def check_const_string(result, func, cargs, offset=None, cpl=False):
    """
    Similar functionality to `check_string`, but does not free the pointer.
    """
    if offset:
        check_err(result, cpl=cpl)
        ptr = ptr_byref(cargs, offset)
        return ptr.value
    else:
        return result


def check_string(result, func, cargs, offset=-1, str_result=False):
    """
    Check the string output returned from the given function, and free
    the string pointer allocated by OGR.  The `str_result` keyword
    may be used when the result is the string pointer, otherwise
    the OGR error code is assumed.  The `offset` keyword may be used
    to extract the string pointer passed in by-reference at the given
    slice offset in the function arguments.
    """
    if str_result:
        # For routines that return a string.
        ptr = result
        if not ptr:
            s = None
        else:
            s = string_at(result)
    else:
        # Error-code return specified.
        check_err(result)
        ptr = ptr_byref(cargs, offset)
        # Getting the string value
        s = ptr.value
    # Correctly freeing the allocated memory behind GDAL pointer
    # with the VSIFree routine.
    if ptr:
        lgdal.VSIFree(ptr)
    return s

# ### DataSource, Layer error-checking ###


# ### Envelope checking ###
def check_envelope(result, func, cargs, offset=-1):
    "Check a function that returns an OGR Envelope by reference."
    env = ptr_byref(cargs, offset)
    return env


# ### Geometry error-checking routines ###
def check_geom(result, func, cargs):
    "Check a function that returns a geometry."
    # OGR_G_Clone may return an integer, even though the
    # restype is set to c_void_p
    if isinstance(result, int):
        result = c_void_p(result)
    if not result:
        raise GDALException('Invalid geometry pointer returned from "%s".' % func.__name__)
    return result


def check_geom_offset(result, func, cargs, offset=-1):
    "Check the geometry at the given offset in the C parameter list."
    check_err(result)
    geom = ptr_byref(cargs, offset=offset)
    return check_geom(geom, func, cargs)


# ### Spatial Reference error-checking routines ###
def check_srs(result, func, cargs):
    if isinstance(result, int):
        result = c_void_p(result)
    if not result:
        raise SRSException('Invalid spatial reference pointer returned from "%s".' % func.__name__)
    return result


# ### Other error-checking routines ###
def check_arg_errcode(result, func, cargs, cpl=False):
    """
    The error code is returned in the last argument, by reference.
    Check its value with `check_err` before returning the result.
    """
    check_err(arg_byref(cargs), cpl=cpl)
    return result


def check_errcode(result, func, cargs, cpl=False):
    """
    Check the error code returned (c_int).
    """
    check_err(result, cpl=cpl)


def check_pointer(result, func, cargs):
    "Make sure the result pointer is valid."
    if isinstance(result, int):
        result = c_void_p(result)
    if result:
        return result
    else:
        raise GDALException('Invalid pointer returned from "%s"' % func.__name__)


def check_str_arg(result, func, cargs):
    """
    This is for the OSRGet[Angular|Linear]Units functions, which
    require that the returned string pointer not be freed.  This
    returns both the double and string values.
    """
    dbl = result
    ptr = cargs[-1]._obj
    return dbl, ptr.value.decode()
