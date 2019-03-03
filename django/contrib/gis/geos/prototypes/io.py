import threading
from ctypes import POINTER, Structure, byref, c_byte, c_char_p, c_int, c_size_t

from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.libgeos import (
    GEOM_PTR, GEOSFuncFactory, geos_version_tuple,
)
from django.contrib.gis.geos.prototypes.errcheck import (
    check_geom, check_sized_string, check_string,
)
from django.contrib.gis.geos.prototypes.geom import c_uchar_p, geos_char_p
from django.utils.encoding import force_bytes


# ### The WKB/WKT Reader/Writer structures and pointers ###
class WKTReader_st(Structure):
    pass


class WKTWriter_st(Structure):
    pass


class WKBReader_st(Structure):
    pass


class WKBWriter_st(Structure):
    pass


WKT_READ_PTR = POINTER(WKTReader_st)
WKT_WRITE_PTR = POINTER(WKTWriter_st)
WKB_READ_PTR = POINTER(WKBReader_st)
WKB_WRITE_PTR = POINTER(WKBReader_st)

# WKTReader routines
wkt_reader_create = GEOSFuncFactory('GEOSWKTReader_create', restype=WKT_READ_PTR)
wkt_reader_destroy = GEOSFuncFactory('GEOSWKTReader_destroy', argtypes=[WKT_READ_PTR])

wkt_reader_read = GEOSFuncFactory(
    'GEOSWKTReader_read', argtypes=[WKT_READ_PTR, c_char_p], restype=GEOM_PTR, errcheck=check_geom
)
# WKTWriter routines
wkt_writer_create = GEOSFuncFactory('GEOSWKTWriter_create', restype=WKT_WRITE_PTR)
wkt_writer_destroy = GEOSFuncFactory('GEOSWKTWriter_destroy', argtypes=[WKT_WRITE_PTR])

wkt_writer_write = GEOSFuncFactory(
    'GEOSWKTWriter_write', argtypes=[WKT_WRITE_PTR, GEOM_PTR], restype=geos_char_p, errcheck=check_string
)

wkt_writer_get_outdim = GEOSFuncFactory(
    'GEOSWKTWriter_getOutputDimension', argtypes=[WKT_WRITE_PTR], restype=c_int
)
wkt_writer_set_outdim = GEOSFuncFactory(
    'GEOSWKTWriter_setOutputDimension', argtypes=[WKT_WRITE_PTR, c_int]
)

wkt_writer_set_trim = GEOSFuncFactory('GEOSWKTWriter_setTrim', argtypes=[WKT_WRITE_PTR, c_byte])
wkt_writer_set_precision = GEOSFuncFactory('GEOSWKTWriter_setRoundingPrecision', argtypes=[WKT_WRITE_PTR, c_int])

# WKBReader routines
wkb_reader_create = GEOSFuncFactory('GEOSWKBReader_create', restype=WKB_READ_PTR)
wkb_reader_destroy = GEOSFuncFactory('GEOSWKBReader_destroy', argtypes=[WKB_READ_PTR])


class WKBReadFunc(GEOSFuncFactory):
    # Although the function definitions take `const unsigned char *`
    # as their parameter, we use c_char_p here so the function may
    # take Python strings directly as parameters.  Inside Python there
    # is not a difference between signed and unsigned characters, so
    # it is not a problem.
    argtypes = [WKB_READ_PTR, c_char_p, c_size_t]
    restype = GEOM_PTR
    errcheck = staticmethod(check_geom)


wkb_reader_read = WKBReadFunc('GEOSWKBReader_read')
wkb_reader_read_hex = WKBReadFunc('GEOSWKBReader_readHEX')

# WKBWriter routines
wkb_writer_create = GEOSFuncFactory('GEOSWKBWriter_create', restype=WKB_WRITE_PTR)
wkb_writer_destroy = GEOSFuncFactory('GEOSWKBWriter_destroy', argtypes=[WKB_WRITE_PTR])


# WKB Writing prototypes.
class WKBWriteFunc(GEOSFuncFactory):
    argtypes = [WKB_WRITE_PTR, GEOM_PTR, POINTER(c_size_t)]
    restype = c_uchar_p
    errcheck = staticmethod(check_sized_string)


wkb_writer_write = WKBWriteFunc('GEOSWKBWriter_write')
wkb_writer_write_hex = WKBWriteFunc('GEOSWKBWriter_writeHEX')


# WKBWriter property getter/setter prototypes.
class WKBWriterGet(GEOSFuncFactory):
    argtypes = [WKB_WRITE_PTR]
    restype = c_int


class WKBWriterSet(GEOSFuncFactory):
    argtypes = [WKB_WRITE_PTR, c_int]


wkb_writer_get_byteorder = WKBWriterGet('GEOSWKBWriter_getByteOrder')
wkb_writer_set_byteorder = WKBWriterSet('GEOSWKBWriter_setByteOrder')
wkb_writer_get_outdim = WKBWriterGet('GEOSWKBWriter_getOutputDimension')
wkb_writer_set_outdim = WKBWriterSet('GEOSWKBWriter_setOutputDimension')
wkb_writer_get_include_srid = WKBWriterGet('GEOSWKBWriter_getIncludeSRID', restype=c_byte)
wkb_writer_set_include_srid = WKBWriterSet('GEOSWKBWriter_setIncludeSRID', argtypes=[WKB_WRITE_PTR, c_byte])


# ### Base I/O Class ###
class IOBase(GEOSBase):
    "Base class for GEOS I/O objects."
    def __init__(self):
        # Getting the pointer with the constructor.
        self.ptr = self._constructor()
        # Loading the real destructor function at this point as doing it in
        # __del__ is too late (import error).
        self.destructor.func

# ### Base WKB/WKT Reading and Writing objects ###


# Non-public WKB/WKT reader classes for internal use because
# their `read` methods return _pointers_ instead of GEOSGeometry
# objects.
class _WKTReader(IOBase):
    _constructor = wkt_reader_create
    ptr_type = WKT_READ_PTR
    destructor = wkt_reader_destroy

    def read(self, wkt):
        if not isinstance(wkt, (bytes, str)):
            raise TypeError
        return wkt_reader_read(self.ptr, force_bytes(wkt))


class _WKBReader(IOBase):
    _constructor = wkb_reader_create
    ptr_type = WKB_READ_PTR
    destructor = wkb_reader_destroy

    def read(self, wkb):
        "Return a _pointer_ to C GEOS Geometry object from the given WKB."
        if isinstance(wkb, memoryview):
            wkb_s = bytes(wkb)
            return wkb_reader_read(self.ptr, wkb_s, len(wkb_s))
        elif isinstance(wkb, (bytes, str)):
            return wkb_reader_read_hex(self.ptr, wkb, len(wkb))
        else:
            raise TypeError


# ### WKB/WKT Writer Classes ###
class WKTWriter(IOBase):
    _constructor = wkt_writer_create
    ptr_type = WKT_WRITE_PTR
    destructor = wkt_writer_destroy

    _trim = False
    _precision = None

    def __init__(self, dim=2, trim=False, precision=None):
        super().__init__()
        if bool(trim) != self._trim:
            self.trim = trim
        if precision is not None:
            self.precision = precision
        self.outdim = dim

    def write(self, geom):
        "Return the WKT representation of the given geometry."
        return wkt_writer_write(self.ptr, geom.ptr)

    @property
    def outdim(self):
        return wkt_writer_get_outdim(self.ptr)

    @outdim.setter
    def outdim(self, new_dim):
        if new_dim not in (2, 3):
            raise ValueError('WKT output dimension must be 2 or 3')
        wkt_writer_set_outdim(self.ptr, new_dim)

    @property
    def trim(self):
        return self._trim

    @trim.setter
    def trim(self, flag):
        if bool(flag) != self._trim:
            self._trim = bool(flag)
            wkt_writer_set_trim(self.ptr, self._trim)

    @property
    def precision(self):
        return self._precision

    @precision.setter
    def precision(self, precision):
        if (not isinstance(precision, int) or precision < 0) and precision is not None:
            raise AttributeError('WKT output rounding precision must be non-negative integer or None.')
        if precision != self._precision:
            self._precision = precision
            wkt_writer_set_precision(self.ptr, -1 if precision is None else precision)


class WKBWriter(IOBase):
    _constructor = wkb_writer_create
    ptr_type = WKB_WRITE_PTR
    destructor = wkb_writer_destroy
    geos_version = geos_version_tuple()

    def __init__(self, dim=2):
        super().__init__()
        self.outdim = dim

    def _handle_empty_point(self, geom):
        from django.contrib.gis.geos import Point
        if isinstance(geom, Point) and geom.empty:
            if self.srid:
                # PostGIS uses POINT(NaN NaN) for WKB representation of empty
                # points. Use it for EWKB as it's a PostGIS specific format.
                # https://trac.osgeo.org/postgis/ticket/3181
                geom = Point(float('NaN'), float('NaN'), srid=geom.srid)
            else:
                raise ValueError('Empty point is not representable in WKB.')
        return geom

    def write(self, geom):
        "Return the WKB representation of the given geometry."
        from django.contrib.gis.geos import Polygon
        geom = self._handle_empty_point(geom)
        wkb = wkb_writer_write(self.ptr, geom.ptr, byref(c_size_t()))
        if self.geos_version < (3, 6, 1) and isinstance(geom, Polygon) and geom.empty:
            # Fix GEOS output for empty polygon.
            # See https://trac.osgeo.org/geos/ticket/680.
            wkb = wkb[:-8] + b'\0' * 4
        return memoryview(wkb)

    def write_hex(self, geom):
        "Return the HEXEWKB representation of the given geometry."
        from django.contrib.gis.geos.polygon import Polygon
        geom = self._handle_empty_point(geom)
        wkb = wkb_writer_write_hex(self.ptr, geom.ptr, byref(c_size_t()))
        if self.geos_version < (3, 6, 1) and isinstance(geom, Polygon) and geom.empty:
            wkb = wkb[:-16] + b'0' * 8
        return wkb

    # ### WKBWriter Properties ###

    # Property for getting/setting the byteorder.
    def _get_byteorder(self):
        return wkb_writer_get_byteorder(self.ptr)

    def _set_byteorder(self, order):
        if order not in (0, 1):
            raise ValueError('Byte order parameter must be 0 (Big Endian) or 1 (Little Endian).')
        wkb_writer_set_byteorder(self.ptr, order)

    byteorder = property(_get_byteorder, _set_byteorder)

    # Property for getting/setting the output dimension.
    @property
    def outdim(self):
        return wkb_writer_get_outdim(self.ptr)

    @outdim.setter
    def outdim(self, new_dim):
        if new_dim not in (2, 3):
            raise ValueError('WKB output dimension must be 2 or 3')
        wkb_writer_set_outdim(self.ptr, new_dim)

    # Property for getting/setting the include srid flag.
    @property
    def srid(self):
        return bool(wkb_writer_get_include_srid(self.ptr))

    @srid.setter
    def srid(self, include):
        wkb_writer_set_include_srid(self.ptr, bool(include))


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


thread_context = ThreadLocalIO()


# These module-level routines return the I/O object that is local to the
# thread. If the I/O object does not exist yet it will be initialized.
def wkt_r():
    thread_context.wkt_r = thread_context.wkt_r or _WKTReader()
    return thread_context.wkt_r


def wkt_w(dim=2, trim=False, precision=None):
    if not thread_context.wkt_w:
        thread_context.wkt_w = WKTWriter(dim=dim, trim=trim, precision=precision)
    else:
        thread_context.wkt_w.outdim = dim
        thread_context.wkt_w.trim = trim
        thread_context.wkt_w.precision = precision
    return thread_context.wkt_w


def wkb_r():
    thread_context.wkb_r = thread_context.wkb_r or _WKBReader()
    return thread_context.wkb_r


def wkb_w(dim=2):
    if not thread_context.wkb_w:
        thread_context.wkb_w = WKBWriter(dim=dim)
    else:
        thread_context.wkb_w.outdim = dim
    return thread_context.wkb_w


def ewkb_w(dim=2):
    if not thread_context.ewkb_w:
        thread_context.ewkb_w = WKBWriter(dim=dim)
        thread_context.ewkb_w.srid = True
    else:
        thread_context.ewkb_w.outdim = dim
    return thread_context.ewkb_w
