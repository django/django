"""
Module that holds classes for performing I/O operations on GEOS geometry
objects.  Specifically, this has Python implementations of WKB/WKT
reader and writer classes.
"""
from ctypes import byref, c_size_t
from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.geos.libgeos import GEOM_PTR
from django.contrib.gis.geos.prototypes import io as capi

class IOBase(GEOSBase):
    "Base class for GEOS I/O objects."
    def __init__(self):
        # Getting the pointer with the constructor.
        self.ptr = self._constructor()

    def __del__(self):
        # Cleaning up with the appropriate destructor.
        if self._ptr: self._destructor(self._ptr)

### WKT Reading and Writing objects ###

# Non-public class for internal use because its `read` method returns
# _pointers_ instead of a GEOSGeometry object.
class _WKTReader(IOBase):
    _constructor = capi.wkt_reader_create
    _destructor = capi.wkt_reader_destroy
    ptr_type = capi.WKT_READ_PTR

    def read(self, wkt):
        if not isinstance(wkt, basestring): raise TypeError
        return capi.wkt_reader_read(self.ptr, wkt)

class WKTReader(_WKTReader):
    def read(self, wkt):
        "Returns a GEOSGeometry for the given WKT string."
        return GEOSGeometry(super(WKTReader, self).read(wkt))

class WKTWriter(IOBase):
    _constructor = capi.wkt_writer_create
    _destructor = capi.wkt_writer_destroy
    ptr_type = capi.WKT_WRITE_PTR

    def write(self, geom):
        "Returns the WKT representation of the given geometry."
        return capi.wkt_writer_write(self.ptr, geom.ptr)

### WKB Reading and Writing objects ###

# Non-public class for the same reason as _WKTReader above.
class _WKBReader(IOBase):
    _constructor = capi.wkb_reader_create
    _destructor = capi.wkb_reader_destroy
    ptr_type = capi.WKB_READ_PTR

    def read(self, wkb):
        "Returns a _pointer_ to C GEOS Geometry object from the given WKB."
        if isinstance(wkb, buffer):
            wkb_s = str(wkb)
            return capi.wkb_reader_read(self.ptr, wkb_s, len(wkb_s))
        elif isinstance(wkb, basestring):
            return capi.wkb_reader_read_hex(self.ptr, wkb, len(wkb))
        else:
            raise TypeError

class WKBReader(_WKBReader):
    def read(self, wkb):
        "Returns a GEOSGeometry for the given WKB buffer."
        return GEOSGeometry(super(WKBReader, self).read(wkb))

class WKBWriter(IOBase):
    _constructor = capi.wkb_writer_create
    _destructor = capi.wkb_writer_destroy
    ptr_type = capi.WKB_WRITE_PTR

    def write(self, geom):
        "Returns the WKB representation of the given geometry."
        return buffer(capi.wkb_writer_write(self.ptr, geom.ptr, byref(c_size_t())))

    def write_hex(self, geom):
        "Returns the HEXEWKB representation of the given geometry."
        return capi.wkb_writer_write_hex(self.ptr, geom.ptr, byref(c_size_t()))

    ### WKBWriter Properties ###

    # Property for getting/setting the byteorder.
    def _get_byteorder(self):
        return capi.wkb_writer_get_byteorder(self.ptr)

    def _set_byteorder(self, order):
        if not order in (0, 1): raise ValueError('Byte order parameter must be 0 (Big Endian) or 1 (Little Endian).')
        capi.wkb_writer_set_byteorder(self.ptr, order)

    byteorder = property(_get_byteorder, _set_byteorder)

    # Property for getting/setting the output dimension.
    def _get_outdim(self):
        return capi.wkb_writer_get_outdim(self.ptr)

    def _set_outdim(self, new_dim):
        if not new_dim in (2, 3): raise ValueError('WKB output dimension must be 2 or 3')
        capi.wkb_writer_set_outdim(self.ptr, new_dim)

    outdim = property(_get_outdim, _set_outdim)

    # Property for getting/setting the include srid flag.
    def _get_include_srid(self):
        return bool(ord(capi.wkb_writer_get_include_srid(self.ptr)))

    def _set_include_srid(self, include):
        if bool(include): flag = chr(1)
        else: flag = chr(0)
        capi.wkb_writer_set_include_srid(self.ptr, flag)

    srid = property(_get_include_srid, _set_include_srid)

# Instances of the WKT and WKB reader/writer objects.
wkt_r = _WKTReader()
wkt_w = WKTWriter()
wkb_r = _WKBReader()
wkb_w = WKBWriter()

# These instances are for writing EWKB in 2D and 3D.
ewkb_w = WKBWriter()
ewkb_w.srid = True
ewkb_w3d = WKBWriter()
ewkb_w3d.srid = True
ewkb_w3d.outdim = 3
