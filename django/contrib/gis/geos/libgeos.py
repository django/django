"""
  This module houses the ctypes initialization procedures, as well
  as the notice and error handler function callbacks (get called
  when an error occurs in GEOS).
"""

from django.contrib.gis.geos.GEOSError import GEOSException
from ctypes import \
     c_char_p, c_int, c_size_t, c_ubyte, pointer, addressof, \
     CDLL, CFUNCTYPE, POINTER, Structure
import os, sys

# NumPy supported?
try:
    from numpy import array, ndarray
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

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
#  we need to wrap:
#  "extern void GEOS_DLL initGEOS(GEOSMessageHandler notice_function, GEOSMessageHandler error_function);"
lgeos.initGEOS(notice_h, error_h)

class GEOSPointer(object):
    """The GEOSPointer provides a layer of abstraction to accessing the values returned by
    GEOS geometry creation routines."""

    ### Python 'magic' routines ###
    def __init__(self, ptr):
        "Given a ctypes pointer(c_int)"
        if isinstance(ptr, int):
            self._ptr = pointer(c_int(ptr))
        else:
            raise TypeError, 'GEOSPointer object must initialize with an integer.'
        
    def __call__(self):
        """If the pointer is NULL, then an exception will be raised, otherwise the
        address value (a GEOSGeom_ptr) will be returned."""
        if self.valid: return self.address
        else: raise GEOSException, 'GEOS pointer no longer valid (was the parent geometry deleted?)'

    ### GEOSPointer Properties ###
    @property
    def address(self):
        "Returns the address of the GEOSPointer (represented as an integer)."
        return self._ptr.contents.value

    @property
    def valid(self):
        "Tests whether this GEOSPointer is valid."
        if bool(self.address): return True
        else: return False
    
    ### GEOSPointer Methods ###
    def set(self, address):
        "Sets this pointer with the new address (represented as an integer)"
        if not isinstance(address, int):
            raise TypeError, 'GEOSPointer must be set with an address (an integer).'
        self._ptr.contents = c_int(address)

    def nullify(self):
        "Nullify this geometry pointer (set the address to 0)."
        self.set(0)
