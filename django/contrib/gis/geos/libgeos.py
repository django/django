"""
  This module houses the ctypes initialization procedures, as well
   as the notice and error handler function callbacks (get called
   when an error occurs in GEOS).

  This module also houses GEOS Pointer utilities, including
   get_pointer_arr(), and GEOM_PTR.
"""

from django.contrib.gis.geos.error import GEOSException
from ctypes import c_char_p, c_int, string_at, CDLL, CFUNCTYPE, POINTER, Structure
import atexit, os, sys

# NumPy supported?
try:
    from numpy import array, ndarray
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# Is psycopg2 available?
try:
    from psycopg2.extensions import ISQLQuote
except (ImportError, EnvironmentError):
    ISQLQuote = None

# Setting the appropriate name for the GEOS-C library, depending on which
# OS and POSIX platform we're running.
if os.name == 'nt':
    # Windows NT library
    lib_name = 'libgeos_c-1.dll'
elif os.name == 'posix':
    platform = os.uname()[0] # Using os.uname()
    if platform in ('Linux', 'SunOS'):
        # Linux or Solaris shared library
        lib_name = 'libgeos_c.so'
    elif platform == 'Darwin':
        # Mac OSX Shared Library (Thanks Matt!)
        lib_name = 'libgeos_c.dylib'
    else:
        raise GEOSException, 'Unknown POSIX platform "%s"' % platform
else:
    raise GEOSException, 'Unsupported OS "%s"' % os.name

# Getting the GEOS C library.  The C interface (CDLL) is used for
#  both *NIX and Windows.
# See the GEOS C API source code for more details on the library function calls:
#  http://geos.refractions.net/ro/doxygen_docs/html/geos__c_8h-source.html
lgeos = CDLL(lib_name)

# The notice and error handler C function callback definitions.
#  Supposed to mimic the GEOS message handler (C below):
#  "typedef void (*GEOSMessageHandler)(const char *fmt, ...);"
NOTICEFUNC = CFUNCTYPE(None, c_char_p, c_char_p)
def notice_h(fmt, list, output_h=sys.stdout):
    output_h.write('GEOS_NOTICE: %s\n' % (fmt % list))
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

# Opaque GEOS geometry structure
class GEOSGeom_t(Structure): 
    "Opaque structure used when arrays of geometries are needed as parameters."
    pass

# Pointer to opaque geometry structure
GEOM_PTR = POINTER(GEOSGeom_t)

# Used specifically by the GEOSGeom_createPolygon and GEOSGeom_createCollection 
#  GEOS routines
def get_pointer_arr(n):
    "Gets a ctypes pointer array (of length `n`) for GEOSGeom_t opaque pointer."
    GeomArr = GEOM_PTR * n
    return GeomArr()

def geos_version():
    "Returns the string version of GEOS."
    return string_at(lgeos.GEOSversion())

# Calling the finishGEOS() upon exit of the interpreter.
atexit.register(lgeos.finishGEOS)
