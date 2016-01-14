"""
 This module houses the ctypes initialization procedures, as well
 as the notice and error handler function callbacks (get called
 when an error occurs in GEOS).

 This module also houses GEOS Pointer utilities, including
 get_pointer_arr(), and GEOM_PTR.
"""
import logging
import os
import re
from ctypes import CDLL, CFUNCTYPE, POINTER, Structure, c_char_p
from ctypes.util import find_library

from django.contrib.gis.geos.error import GEOSException
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import SimpleLazyObject

logger = logging.getLogger('django.contrib.gis')


def load_geos():
    # Custom library path set?
    try:
        from django.conf import settings
        lib_path = settings.GEOS_LIBRARY_PATH
    except (AttributeError, EnvironmentError,
            ImportError, ImproperlyConfigured):
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
    #  http://geos.refractions.net/ro/doxygen_docs/html/geos__c_8h-source.html
    _lgeos = CDLL(lib_path)
    # Here we set up the prototypes for the initGEOS_r and finishGEOS_r
    # routines.  These functions aren't actually called until they are
    # attached to a GEOS context handle -- this actually occurs in
    # geos/prototypes/threadsafe.py.
    _lgeos.initGEOS_r.restype = CONTEXT_PTR
    _lgeos.finishGEOS_r.argtypes = [CONTEXT_PTR]
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


# Used specifically by the GEOSGeom_createPolygon and GEOSGeom_createCollection
#  GEOS routines
def get_pointer_arr(n):
    "Gets a ctypes pointer array (of length `n`) for GEOSGeom_t opaque pointer."
    GeomArr = GEOM_PTR * n
    return GeomArr()


lgeos = SimpleLazyObject(load_geos)


class GEOSFuncFactory(object):
    """
    Lazy loading of GEOS functions.
    """
    argtypes = None
    restype = None
    errcheck = None

    def __init__(self, func_name, *args, **kwargs):
        self.func_name = func_name
        self.restype = kwargs.pop('restype', self.restype)
        self.errcheck = kwargs.pop('errcheck', self.errcheck)
        self.argtypes = kwargs.pop('argtypes', self.argtypes)
        self.args = args
        self.kwargs = kwargs
        self.func = None

    def __call__(self, *args, **kwargs):
        if self.func is None:
            self.func = self.get_func(*self.args, **self.kwargs)
        return self.func(*args, **kwargs)

    def get_func(self, *args, **kwargs):
        from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc
        func = GEOSFunc(self.func_name)
        func.argtypes = self.argtypes or []
        func.restype = self.restype
        if self.errcheck:
            func.errcheck = self.errcheck
        return func


# Returns the string version of the GEOS library. Have to set the restype
# explicitly to c_char_p to ensure compatibility across 32 and 64-bit platforms.
geos_version = GEOSFuncFactory('GEOSversion', restype=c_char_p)

# Regular expression should be able to parse version strings such as
# '3.0.0rc4-CAPI-1.3.3', '3.0.0-CAPI-1.4.1', '3.4.0dev-CAPI-1.8.0' or '3.4.0dev-CAPI-1.8.0 r0'
version_regex = re.compile(
    r'^(?P<version>(?P<major>\d+)\.(?P<minor>\d+)\.(?P<subminor>\d+))'
    r'((rc(?P<release_candidate>\d+))|dev)?-CAPI-(?P<capi_version>\d+\.\d+\.\d+)( r\d+)?$'
)


def geos_version_info():
    """
    Returns a dictionary containing the various version metadata parsed from
    the GEOS version string, including the version number, whether the version
    is a release candidate (and what number release candidate), and the C API
    version.
    """
    ver = geos_version().decode()
    m = version_regex.match(ver)
    if not m:
        raise GEOSException('Could not parse version info string "%s"' % ver)
    return {key: m.group(key) for key in (
        'version', 'release_candidate', 'capi_version', 'major', 'minor', 'subminor')}
