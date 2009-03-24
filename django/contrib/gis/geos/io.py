"""
Module that holds classes for performing I/O operations on GEOS geometry
objects.  Specifically, this has Python implementations of WKB/WKT
reader and writer classes.
"""
from ctypes import byref, c_size_t
from django.contrib.gis.geos.base import GEOSBase
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.libgeos import GEOM_PTR
from django.contrib.gis.geos.prototypes import io as capi

class IOBase(GEOSBase):
    "Base class for IO objects that that have `destroy` method."
    def __init__(self):
        # Getting the pointer with the constructor.
        self.ptr = self.constructor()

    def __del__(self):
        # Cleaning up with the appropriate destructor.
        if self._ptr: self.destructor(self._ptr)

    def _get_geom_ptr(self, geom):
        if hasattr(geom, 'ptr'): geom = geom.ptr
        if not isinstance(geom, GEOM_PTR): raise TypeError
        return geom

### WKT Reading and Writing objects ###
class WKTReader(IOBase):
    constructor = capi.wkt_reader_create
    destructor = capi.wkt_reader_destroy
    ptr_type = capi.WKT_READ_PTR

    def read(self, wkt, ptr=False):
        if not isinstance(wkt, basestring): raise TypeError
        return capi.wkt_reader_read(self.ptr, wkt)

class WKTWriter(IOBase):
    constructor = capi.wkt_writer_create
    destructor = capi.wkt_writer_destroy
    ptr_type = capi.WKT_WRITE_PTR

    def write(self, geom):
        return capi.wkt_writer_write(self.ptr, self._get_geom_ptr(geom))

### WKB Reading and Writing objects ###
class WKBReader(IOBase):
    constructor = capi.wkb_reader_create
    destructor = capi.wkb_reader_destroy
    ptr_type = capi.WKB_READ_PTR

    def read(self, wkb):
        if isinstance(wkb, buffer):
            wkb_s = str(wkb)
            return capi.wkb_reader_read(self.ptr, wkb_s, len(wkb_s))
        elif isinstance(wkb, basestring):
            return capi.wkb_reader_read_hex(self.ptr, wkb, len(wkb))
        else:
            raise TypeError

class WKBWriter(IOBase):
    constructor = capi.wkb_writer_create
    destructor = capi.wkb_writer_destroy
    ptr_type = capi.WKB_READ_PTR

    def write(self, geom):
        return buffer(capi.wkb_writer_write(self.ptr, self._get_geom_ptr(geom), byref(c_size_t())))

    def write_hex(self, geom):
        return capi.wkb_writer_write_hex(self.ptr, self._get_geom_ptr(geom), byref(c_size_t()))

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
wkt_r = WKTReader()
wkt_w = WKTWriter()
wkb_r = WKBReader()
wkb_w = WKBWriter()

