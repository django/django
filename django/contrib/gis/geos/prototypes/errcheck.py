"""
 Error checking functions for GEOS ctypes prototype functions.
"""
import os
from ctypes import string_at, CDLL
from ctypes.util import find_library
from django.contrib.gis.geos.error import GEOSException

# Getting the C library, needed to free the string pointers
# returned from GEOS.
if os.name == 'nt':
    libc_name = 'msvcrt'
else:
    libc_name = 'libc'
libc = CDLL(find_library(libc_name))

### ctypes error checking routines ###
def last_arg_byref(args):
    "Returns the last C argument's by reference value."
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
    libc.free(result)
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
    libc.free(result)
    return s

def check_zero(result, func, cargs):
    "Error checking on routines that should not return 0."
    if result == 0:
        raise GEOSException('Error encountered in GEOS C function "%s".' % func.__name__)
    else:
        return result
