"""
 This module houses the ctypes initialization procedures, as well
 as the notice and error handler function callbacks (get called
 when an error occurs in GEOS).

 This module also houses GEOS Pointer utilities, including
 get_pointer_arr(), and GEOM_PTR.
"""
import logging
import os
from ctypes import CDLL, CFUNCTYPE, POINTER, Structure, c_char_p
from ctypes.util import find_library

from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import SimpleLazyObject, cached_property
from django.utils.version import get_version_tuple

logger = logging.getLogger('django.contrib.gis')


def load_geos():
    # Custom library path set?
    try:
        from django.conf import settings
        lib_path = settings.GEOS_LIBRARY_PATH
    except (AttributeError, ImportError, ImproperlyConfigured, OSError):
        lib_path = None

    # Setting the appropriate names for the GEOS-C library.
    if lib_path:
        lib_names = None
    elif os.name == 'nt':
        # Windows NT libraries
        lib_names = ['geos_c', 'libgeos_c-1']
    elif os.name == 'posix':
        # *NIX libraries
        lib_names = ['geos_c', 'GEOS']
    else:
        raise ImportError('Unsupported OS "%s"' % os.name)

    # Using the ctypes `find_library` utility to find the path to the GEOS
    # shared library.  This is better than manually specifying each library name
    # and extension (e.g., libgeos_c.[so|so.1|dylib].).
    if lib_names:
        for lib_name in lib_names:
            lib_path = find_library(lib_name)
            if lib_path is not None:
                break

    # No GEOS library could be found.
    if lib_path is None:
        raise ImportError(
            'Could not find the GEOS library (tried "%s"). '
            'Try setting GEOS_LIBRARY_PATH in your settings.' %
            '", "'.join(lib_names)
        )
    # Getting the GEOS C library.  The C interface (CDLL) is used for
    # both *NIX and Windows.
    # See the GEOS C API source code for more details on the library function calls:
    # https://geos.osgeo.org/doxygen/geos__c_8h_source.html
    _lgeos = CDLL(lib_path)
    # Here we set up the prototypes for the initGEOS_r and finishGEOS_r
    # routines.  These functions aren't actually called until they are
    # attached to a GEOS context handle -- this actually occurs in
    # geos/prototypes/threadsafe.py.
    _lgeos.initGEOS_r.restype = CONTEXT_PTR
    _lgeos.finishGEOS_r.argtypes = [CONTEXT_PTR]
    # Set restype for compatibility across 32 and 64-bit platforms.
    _lgeos.GEOSversion.restype = c_char_p
    return _lgeos


# The notice and error handler C function callback definitions.
# Supposed to mimic the GEOS message handler (C below):
#  typedef void (*GEOSMessageHandler)(const char *fmt, ...);
NOTICEFUNC = CFUNCTYPE(None, c_char_p, c_char_p)


def notice_h(fmt, lst):
    fmt, lst = fmt.decode(), lst.decode()
    try:
        warn_msg = fmt % lst
    except TypeError:
        warn_msg = fmt
    logger.warning('GEOS_NOTICE: %s\n', warn_msg)


notice_h = NOTICEFUNC(notice_h)

ERRORFUNC = CFUNCTYPE(None, c_char_p, c_char_p)


def error_h(fmt, lst):
    fmt, lst = fmt.decode(), lst.decode()
    try:
        err_msg = fmt % lst
    except TypeError:
        err_msg = fmt
    logger.error('GEOS_ERROR: %s\n', err_msg)


error_h = ERRORFUNC(error_h)

# #### GEOS Geometry C data structures, and utility functions. ####


# Opaque GEOS geometry structures, used for GEOM_PTR and CS_PTR
class GEOSGeom_t(Structure):
    pass


class GEOSPrepGeom_t(Structure):
    pass


class GEOSCoordSeq_t(Structure):
    pass


class GEOSContextHandle_t(Structure):
    pass


# Pointers to opaque GEOS geometry structures.
GEOM_PTR = POINTER(GEOSGeom_t)
PREPGEOM_PTR = POINTER(GEOSPrepGeom_t)
CS_PTR = POINTER(GEOSCoordSeq_t)
CONTEXT_PTR = POINTER(GEOSContextHandle_t)


lgeos = SimpleLazyObject(load_geos)


class GEOSFuncFactory:
    """
    Lazy loading of GEOS functions.
    """
    argtypes = None
    restype = None
    errcheck = None

    def __init__(self, func_name, *, restype=None, errcheck=None, argtypes=None):
        self.func_name = func_name
        if restype is not None:
            self.restype = restype
        if errcheck is not None:
            self.errcheck = errcheck
        if argtypes is not None:
            self.argtypes = argtypes

    def __call__(self, *args):
        return self.func(*args)

    @cached_property
    def func(self):
        from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc
        func = GEOSFunc(self.func_name)
        func.argtypes = self.argtypes or []
        func.restype = self.restype
        if self.errcheck:
            func.errcheck = self.errcheck
        return func


def geos_version():
    """Return the string version of the GEOS library."""
    return lgeos.GEOSversion()


def geos_version_tuple():
    """Return the GEOS version as a tuple (major, minor, subminor)."""
    return get_version_tuple(geos_version().decode())
