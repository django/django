"""
 This module houses the ctypes initialization procedures, as well
 as the notice and error handler function callbacks (get called
 when an error occurs in GEOS).

 This module also houses GEOS Pointer utilities, including
 get_pointer_arr(), and GEOM_PTR.
"""
import atexit, os, re, sys
from ctypes import c_char_p, Structure, CDLL, CFUNCTYPE, POINTER
from ctypes.util import find_library
from django.contrib.gis.geos.error import GEOSException

# Custom library path set?
try:
    from django.conf import settings
    lib_path = settings.GEOS_LIBRARY_PATH
except (AttributeError, EnvironmentError, ImportError):
    lib_path = None

# Setting the appropriate names for the GEOS-C library.
if lib_path:
    lib_names = None
elif os.name == 'nt':
    # Windows NT libraries
    lib_names = ['libgeos_c-1']
elif os.name == 'posix':
    # *NIX libraries
    lib_names = ['geos_c', 'GEOS']
else:
    raise ImportError('Unsupported OS "%s"' % os.name)

# Using the ctypes `find_library` utility to find the path to the GEOS
# shared library.  This is better than manually specifiying each library name
# and extension (e.g., libgeos_c.[so|so.1|dylib].).
if lib_names:
    for lib_name in lib_names:
        lib_path = find_library(lib_name)
        if not lib_path is None: break

# No GEOS library could be found.
if lib_path is None:
    raise ImportError('Could not find the GEOS library (tried "%s"). '
                        'Try setting GEOS_LIBRARY_PATH in your settings.' %
                        '", "'.join(lib_names))

# Getting the GEOS C library.  The C interface (CDLL) is used for
#  both *NIX and Windows.
# See the GEOS C API source code for more details on the library function calls:
#  http://geos.refractions.net/ro/doxygen_docs/html/geos__c_8h-source.html
lgeos = CDLL(lib_path)

# The notice and error handler C function callback definitions.
#  Supposed to mimic the GEOS message handler (C below):
#  "typedef void (*GEOSMessageHandler)(const char *fmt, ...);"
NOTICEFUNC = CFUNCTYPE(None, c_char_p, c_char_p)
def notice_h(fmt, lst, output_h=sys.stdout):
    try:
        warn_msg = fmt % lst
    except:
        warn_msg = fmt
    output_h.write('GEOS_NOTICE: %s\n' % warn_msg)
notice_h = NOTICEFUNC(notice_h)

ERRORFUNC = CFUNCTYPE(None, c_char_p, c_char_p)
def error_h(fmt, lst, output_h=sys.stderr):
    try:
        err_msg = fmt % lst
    except:
        err_msg = fmt
    output_h.write('GEOS_ERROR: %s\n' % err_msg)
error_h = ERRORFUNC(error_h)

# The initGEOS routine should be called first, however, that routine takes
#  the notice and error functions as parameters.  Here is the C code that
#  is wrapped:
#  "extern void GEOS_DLL initGEOS(GEOSMessageHandler notice_function, GEOSMessageHandler error_function);"
lgeos.initGEOS(notice_h, error_h)

#### GEOS Geometry C data structures, and utility functions. ####

# Opaque GEOS geometry structures, used for GEOM_PTR and CS_PTR
class GEOSGeom_t(Structure): pass
class GEOSPrepGeom_t(Structure): pass
class GEOSCoordSeq_t(Structure): pass

# Pointers to opaque GEOS geometry structures.
GEOM_PTR = POINTER(GEOSGeom_t)
PREPGEOM_PTR = POINTER(GEOSPrepGeom_t)
CS_PTR = POINTER(GEOSCoordSeq_t)

# Used specifically by the GEOSGeom_createPolygon and GEOSGeom_createCollection
#  GEOS routines
def get_pointer_arr(n):
    "Gets a ctypes pointer array (of length `n`) for GEOSGeom_t opaque pointer."
    GeomArr = GEOM_PTR * n
    return GeomArr()

# Returns the string version of the GEOS library. Have to set the restype
# explicitly to c_char_p to ensure compatibility accross 32 and 64-bit platforms.
geos_version = lgeos.GEOSversion
geos_version.argtypes = None
geos_version.restype = c_char_p

# Regular expression should be able to parse version strings such as
# '3.0.0rc4-CAPI-1.3.3', or '3.0.0-CAPI-1.4.1'
version_regex = re.compile(r'^(?P<version>(?P<major>\d+)\.(?P<minor>\d+)\.\d+)(rc(?P<release_candidate>\d+))?-CAPI-(?P<capi_version>\d+\.\d+\.\d+)$')
def geos_version_info():
    """
    Returns a dictionary containing the various version metadata parsed from
    the GEOS version string, including the version number, whether the version
    is a release candidate (and what number release candidate), and the C API
    version.
    """
    ver = geos_version()
    m = version_regex.match(ver)
    if not m: raise GEOSException('Could not parse version info string "%s"' % ver)
    return dict((key, m.group(key)) for key in ('version', 'release_candidate', 'capi_version', 'major', 'minor'))

# Version numbers and whether or not prepared geometry support is available.
_verinfo = geos_version_info()
GEOS_MAJOR_VERSION = int(_verinfo['major'])
GEOS_MINOR_VERSION = int(_verinfo['minor'])
del _verinfo
GEOS_PREPARE = GEOS_MAJOR_VERSION > 3 or GEOS_MAJOR_VERSION == 3 and GEOS_MINOR_VERSION >= 1

# Calling the finishGEOS() upon exit of the interpreter.
atexit.register(lgeos.finishGEOS)
