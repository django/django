"""
 Error checking functions for GEOS ctypes prototype functions.
"""
import os
from ctypes import c_void_p, string_at, CDLL
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.libgeos import lgeos, GEOS_VERSION

# Getting the `free` routine used to free the memory allocated for
# string pointers returned by GEOS.
if GEOS_VERSION >= (3, 1, 1):
    # In versions 3.1.1 and above, `GEOSFree` was added to the C API
    # because `free` isn't always available on all platforms.
    free = lgeos.GEOSFree
    free.argtypes = [c_void_p]
    free.restype = None
else:
    # Getting the `free` routine from the C library of the platform.
    if os.name == 'nt':
        # On NT, use the MS C library.
        libc = CDLL('msvcrt')
    else:
        # On POSIX platforms C library is obtained by passing None into `CDLL`.
        libc = CDLL(None)
    free = libc.free

### ctypes error checking routines ###
def last_arg_byref(args):
    "Returns the last C argument's value by reference."
    return args[-1]._obj.value

def check_dbl(result, func, cargs):
    "Checks the status code and returns the double value passed in by reference."
    # Checking the status code
    if result != 1: return None
    # Double passed in by reference, return its value.
    return last_arg_byref(cargs)

def check_geom(result, func, cargs):
    "Error checking on routines that return Geometries."
    if not result:
        raise GEOSException('Error encountered checking Geometry returned from GEOS C function "%s".' % func.__name__)
    return result

def check_minus_one(result, func, cargs):
    "Error checking on routines that should not return -1."
    if result == -1:
        raise GEOSException('Error encountered in GEOS C function "%s".' % func.__name__)
    else:
        return result

def check_predicate(result, func, cargs):
    "Error checking for unary/binary predicate functions."
    val = ord(result) # getting the ordinal from the character
    if val == 1: return True
    elif val == 0: return False
    else:
        raise GEOSException('Error encountered on GEOS C predicate function "%s".' % func.__name__)

def check_sized_string(result, func, cargs):
    """
    Error checking for routines that return explicitly sized strings.

    This frees the memory allocated by GEOS at the result pointer.
    """
    if not result:
        raise GEOSException('Invalid string pointer returned by GEOS C function "%s"' % func.__name__)
    # A c_size_t object is passed in by reference for the second
    # argument on these routines, and its needed to determine the
    # correct size.
    s = string_at(result, last_arg_byref(cargs))
    # Freeing the memory allocated within GEOS
    free(result)
    return s

def check_string(result, func, cargs):
    """
    Error checking for routines that return strings.

    This frees the memory allocated by GEOS at the result pointer.
    """
    if not result: raise GEOSException('Error encountered checking string return value in GEOS C function "%s".' % func.__name__)
    # Getting the string value at the pointer address.
    s = string_at(result)
    # Freeing the memory allocated within GEOS
    free(result)
    return s

def check_zero(result, func, cargs):
    "Error checking on routines that should not return 0."
    if result == 0:
        raise GEOSException('Error encountered in GEOS C function "%s".' % func.__name__)
    else:
        return result
