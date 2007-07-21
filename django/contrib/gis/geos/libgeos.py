"""
  This module houses the ctypes initialization procedures, as well
  as the notice and error handler function callbacks (get called
  when an error occurs in GEOS).
"""

from django.contrib.gis.geos.error import GEOSException
from ctypes import c_char_p, c_int, pointer, CDLL, CFUNCTYPE, POINTER, Structure
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

#### GEOS Geometry Pointer utilities. ####

# Opaque GEOS geometry structure
class GEOSGeom_t(Structure): 
    "Opaque structure used when arrays of geometries are needed as parameters."
    pass
# Pointer to opaque geometry structure
GEOM_PTR = POINTER(GEOSGeom_t)
# Used specifically by the GEOSGeom_createPolygon and GEOSGeom_createCollection GEOS routines
def get_pointer_arr(n):
    "Gets a ctypes pointer array (of length `n`) for GEOSGeom_t opaque pointer."
    GeomArr = GEOM_PTR * n
    return GeomArr()

#### GEOS Pointer object and routines ####
class GEOSPointer(object):
    """The GEOSPointer provides a layer of abstraction in accessing the values returned by
    GEOS geometry creation routines.  Memory addresses (integers) are kept in a C pointer,
    which allows parent geometries to be 'nullified' if their children's memory is used
    in construction of another geometry. Related coordinate sequence pointers are kept
    in this object for the same reason."""

    ### Python 'magic' routines ###
    def __init__(self, address, coordseq=0):
        "Initializes on an address (an integer)."
        if isinstance(address, int):
            self._geom = pointer(c_int(address))
            self._coordseq = pointer(c_int(coordseq))
        else:
            raise TypeError, 'GEOSPointer object must initialize with an integer.'
        
    def __call__(self):
        """If the pointer is NULL, then an exception will be raised, otherwise the
        address value (an integer) will be returned."""
        if self.valid: return self.address
        else: raise GEOSException, 'GEOS pointer no longer valid (was this geometry or the parent geometry deleted or modified?)'

    def __bool__(self):
        "Returns True when the GEOSPointer is valid."
        return self.valid

    def __str__(self):
        return str(self.address)

    ### GEOSPointer Properties ###
    @property
    def address(self):
        "Returns the address of the GEOSPointer (represented as an integer)."
        return self._geom.contents.value

    @property
    def valid(self):
        "Tests whether this GEOSPointer is valid."
        if bool(self.address): return True
        else: return False
    
    ### Coordinate Sequence properties ###
    def coordseq(self):
        "If the coordinate sequence pointer is NULL (0), an exception will be raised."
        if self.coordseq_valid: return self.coordseq_address
        else: raise GEOSException, 'GEOS coordinate sequence pointer invalid (was this geometry or the parent geometry deleted or modified?)'

    @property
    def coordseq_address(self):
        "Returns the address of the related coordinate sequence."
        return self._coordseq.contents.value
    
    @property
    def coordseq_valid(self):
        "Returns True if the coordinate sequence address is valid, False otherwise."
        if bool(self.coordseq_address): return True
        else: return False

    ### GEOSPointer Methods ###
    def set(self, address, coordseq=False):
        "Sets this pointer with the new address (represented as an integer)"
        if not isinstance(address, int):
            raise TypeError, 'GEOSPointer must be set with an address (an integer).'
        if coordseq:
            self._coordseq.contents = c_int(address)
        else:
            self._geom.contents = c_int(address)

    def nullify(self):
        """Nullify this geometry pointer (set the address to 0).  This does not delete
        any memory, rather, it sets the GEOS pointer to a NULL address, to prevent 
        access to addressses of deleted objects."""
        # Nullifying both the geometry and coordinate sequence pointer.
        self.set(0)
        self.set(0, coordseq=True)

def init_from_geom(geom):
    """During initialization of geometries from other geometries, this routine is 
    used to nullify any parent geometries (since they will now be missing memory 
    components) and to nullify the geometry itself to prevent future access.  
    Only the address (an integer) of the current geometry is returned for use in 
    initializing the new geometry."""
    # First getting the memory address of the geometry.
    address = geom._ptr()

    # If the geometry is a child geometry, then the parent geometry pointer is
    #  nullified.
    if geom._parent: geom._parent.nullify()

    # Nullifying the geometry pointer
    geom._ptr.nullify()

    return address
