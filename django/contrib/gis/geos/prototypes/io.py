import threading
from ctypes import byref, c_char_p, c_int, c_char, c_size_t, Structure, POINTER
from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.libgeos import GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_geom, check_string, check_sized_string
from django.contrib.gis.geos.prototypes.geom import c_uchar_p, geos_char_p
from django.contrib.gis.geos.prototypes.threadsafe import GEOSFunc

### The WKB/WKT Reader/Writer structures and pointers ###
class WKTReader_st(Structure): pass
class WKTWriter_st(Structure): pass
class WKBReader_st(Structure): pass
class WKBWriter_st(Structure): pass

WKT_READ_PTR  = POINTER(WKTReader_st)
WKT_WRITE_PTR = POINTER(WKTWriter_st)
WKB_READ_PTR  = POINTER(WKBReader_st)
WKB_WRITE_PTR = POINTER(WKBReader_st)

### WKTReader routines ###
wkt_reader_create = GEOSFunc('GEOSWKTReader_create')
wkt_reader_create.restype = WKT_READ_PTR

wkt_reader_destroy = GEOSFunc('GEOSWKTReader_destroy')
wkt_reader_destroy.argtypes = [WKT_READ_PTR]

wkt_reader_read = GEOSFunc('GEOSWKTReader_read')
wkt_reader_read.argtypes = [WKT_READ_PTR, c_char_p]
wkt_reader_read.restype = GEOM_PTR
wkt_reader_read.errcheck = check_geom

### WKTWriter routines ###
wkt_writer_create = GEOSFunc('GEOSWKTWriter_create')
wkt_writer_create.restype = WKT_WRITE_PTR

wkt_writer_destroy = GEOSFunc('GEOSWKTWriter_destroy')
wkt_writer_destroy.argtypes = [WKT_WRITE_PTR]

wkt_writer_write = GEOSFunc('GEOSWKTWriter_write')
wkt_writer_write.argtypes = [WKT_WRITE_PTR, GEOM_PTR]
wkt_writer_write.restype = geos_char_p
wkt_writer_write.errcheck = check_string

### WKBReader routines ###
wkb_reader_create = GEOSFunc('GEOSWKBReader_create')
wkb_reader_create.restype = WKB_READ_PTR

wkb_reader_destroy = GEOSFunc('GEOSWKBReader_destroy')
wkb_reader_destroy.argtypes = [WKB_READ_PTR]

def wkb_read_func(func):
    # Although the function definitions take `const unsigned char *`
    # as their parameter, we use c_char_p here so the function may
    # take Python strings directly as parameters.  Inside Python there
    # is not a difference between signed and unsigned characters, so
    # it is not a problem.
    func.argtypes = [WKB_READ_PTR, c_char_p, c_size_t]
    func.restype = GEOM_PTR
    func.errcheck = check_geom
    return func

wkb_reader_read = wkb_read_func(GEOSFunc('GEOSWKBReader_read'))
wkb_reader_read_hex = wkb_read_func(GEOSFunc('GEOSWKBReader_readHEX'))

### WKBWriter routines ###
wkb_writer_create = GEOSFunc('GEOSWKBWriter_create')
wkb_writer_create.restype = WKB_WRITE_PTR

wkb_writer_destroy = GEOSFunc('GEOSWKBWriter_destroy')
wkb_writer_destroy.argtypes = [WKB_WRITE_PTR]

# WKB Writing prototypes.
def wkb_write_func(func):
    func.argtypes = [WKB_WRITE_PTR, GEOM_PTR, POINTER(c_size_t)]
    func.restype = c_uchar_p
    func.errcheck = check_sized_string
    return func

wkb_writer_write = wkb_write_func(GEOSFunc('GEOSWKBWriter_write'))
wkb_writer_write_hex = wkb_write_func(GEOSFunc('GEOSWKBWriter_writeHEX'))

# WKBWriter property getter/setter prototypes.
def wkb_writer_get(func, restype=c_int):
    func.argtypes = [WKB_WRITE_PTR]
    func.restype = restype
    return func

def wkb_writer_set(func, argtype=c_int):
    func.argtypes = [WKB_WRITE_PTR, argtype]
    return func

wkb_writer_get_byteorder = wkb_writer_get(GEOSFunc('GEOSWKBWriter_getByteOrder'))
wkb_writer_set_byteorder = wkb_writer_set(GEOSFunc('GEOSWKBWriter_setByteOrder'))
wkb_writer_get_outdim    = wkb_writer_get(GEOSFunc('GEOSWKBWriter_getOutputDimension'))
wkb_writer_set_outdim    = wkb_writer_set(GEOSFunc('GEOSWKBWriter_setOutputDimension'))
wkb_writer_get_include_srid = wkb_writer_get(GEOSFunc('GEOSWKBWriter_getIncludeSRID'), restype=c_char)
wkb_writer_set_include_srid = wkb_writer_set(GEOSFunc('GEOSWKBWriter_setIncludeSRID'), argtype=c_char)

### Base I/O Class ###
class IOBase(GEOSBase):
    "Base class for GEOS I/O objects."
    def __init__(self):
        # Getting the pointer with the constructor.
        self.ptr = self._constructor()

    def __del__(self):
        # Cleaning up with the appropriate destructor.
        if self._ptr: self._destructor(self._ptr)

### Base WKB/WKT Reading and Writing objects ###

# Non-public WKB/WKT reader classes for internal use because
# their `read` methods return _pointers_ instead of GEOSGeometry
# objects.
class _WKTReader(IOBase):
    _constructor = wkt_reader_create
    _destructor = wkt_reader_destroy
    ptr_type = WKT_READ_PTR

    def read(self, wkt):
        if not isinstance(wkt, basestring): raise TypeError
        return wkt_reader_read(self.ptr, wkt)

class _WKBReader(IOBase):
    _constructor = wkb_reader_create
    _destructor = wkb_reader_destroy
    ptr_type = WKB_READ_PTR

    def read(self, wkb):
        "Returns a _pointer_ to C GEOS Geometry object from the given WKB."
        if isinstance(wkb, buffer):
            wkb_s = str(wkb)
            return wkb_reader_read(self.ptr, wkb_s, len(wkb_s))
        elif isinstance(wkb, basestring):
            return wkb_reader_read_hex(self.ptr, wkb, len(wkb))
        else:
            raise TypeError

### WKB/WKT Writer Classes ###
class WKTWriter(IOBase):
    _constructor = wkt_writer_create
    _destructor = wkt_writer_destroy
    ptr_type = WKT_WRITE_PTR

    def write(self, geom):
        "Returns the WKT representation of the given geometry."
        return wkt_writer_write(self.ptr, geom.ptr)

class WKBWriter(IOBase):
    _constructor = wkb_writer_create
    _destructor = wkb_writer_destroy
    ptr_type = WKB_WRITE_PTR

    def write(self, geom):
        "Returns the WKB representation of the given geometry."
        return buffer(wkb_writer_write(self.ptr, geom.ptr, byref(c_size_t())))

    def write_hex(self, geom):
        "Returns the HEXEWKB representation of the given geometry."
        return wkb_writer_write_hex(self.ptr, geom.ptr, byref(c_size_t()))

    ### WKBWriter Properties ###

    # Property for getting/setting the byteorder.
    def _get_byteorder(self):
        return wkb_writer_get_byteorder(self.ptr)

    def _set_byteorder(self, order):
        if not order in (0, 1): raise ValueError('Byte order parameter must be 0 (Big Endian) or 1 (Little Endian).')
        wkb_writer_set_byteorder(self.ptr, order)

    byteorder = property(_get_byteorder, _set_byteorder)

    # Property for getting/setting the output dimension.
    def _get_outdim(self):
        return wkb_writer_get_outdim(self.ptr)

    def _set_outdim(self, new_dim):
        if not new_dim in (2, 3): raise ValueError('WKB output dimension must be 2 or 3')
        wkb_writer_set_outdim(self.ptr, new_dim)

    outdim = property(_get_outdim, _set_outdim)

    # Property for getting/setting the include srid flag.
    def _get_include_srid(self):
        return bool(ord(wkb_writer_get_include_srid(self.ptr)))

    def _set_include_srid(self, include):
        if bool(include): flag = chr(1)
        else: flag = chr(0)
        wkb_writer_set_include_srid(self.ptr, flag)

    srid = property(_get_include_srid, _set_include_srid)

# `ThreadLocalIO` object holds instances of the WKT and WKB reader/writer
# objects that are local to the thread.  The `GEOSGeometry` internals
# access these instances by calling the module-level functions, defined
# below. 
class ThreadLocalIO(threading.local):
    wkt_r = None
    wkt_w = None
    wkb_r = None
    wkb_w = None
    ewkb_w = None
    ewkb_w3d = None

thread_context = ThreadLocalIO()

# These module-level routines return the I/O object that is local to the
# thread. If the I/O object does not exist yet it will be initialized.
def wkt_r():
    if not thread_context.wkt_r:
        thread_context.wkt_r = _WKTReader()
    return thread_context.wkt_r

def wkt_w():
    if not thread_context.wkt_w:
        thread_context.wkt_w = WKTWriter()
    return thread_context.wkt_w

def wkb_r():
    if not thread_context.wkb_r:
        thread_context.wkb_r = _WKBReader()
    return thread_context.wkb_r

def wkb_w():
   if not thread_context.wkb_w:
       thread_context.wkb_w = WKBWriter()
   return thread_context.wkb_w

def ewkb_w():
    if not thread_context.ewkb_w:
        thread_context.ewkb_w = WKBWriter()
        thread_context.ewkb_w.srid = True
    return thread_context.ewkb_w

def ewkb_w3d():
    if not thread_context.ewkb_w3d:
        thread_context.ewkb_w3d = WKBWriter()
        thread_context.ewkb_w3d.srid = True
        thread_context.ewkb_w3d.outdim = 3
    return thread_context.ewkb_w3d
