from ctypes import c_char_p, c_int, c_char, c_size_t, Structure, POINTER
from django.contrib.gis.geos.libgeos import lgeos, GEOM_PTR
from django.contrib.gis.geos.prototypes.errcheck import check_geom, check_string, check_sized_string
from django.contrib.gis.geos.prototypes.geom import c_uchar_p, geos_char_p

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
wkt_reader_create = lgeos.GEOSWKTReader_create
wkt_reader_create.restype = WKT_READ_PTR

wkt_reader_destroy = lgeos.GEOSWKTReader_destroy
wkt_reader_destroy.argtypes = [WKT_READ_PTR]

wkt_reader_read = lgeos.GEOSWKTReader_read
wkt_reader_read.argtypes = [WKT_READ_PTR, c_char_p]
wkt_reader_read.restype = GEOM_PTR
wkt_reader_read.errcheck = check_geom

### WKTWriter routines ###
wkt_writer_create = lgeos.GEOSWKTWriter_create
wkt_writer_create.restype = WKT_WRITE_PTR

wkt_writer_destroy = lgeos.GEOSWKTWriter_destroy
wkt_writer_destroy.argtypes = [WKT_WRITE_PTR]

wkt_writer_write = lgeos.GEOSWKTWriter_write
wkt_writer_write.argtypes = [WKT_WRITE_PTR, GEOM_PTR]
wkt_writer_write.restype = geos_char_p
wkt_writer_write.errcheck = check_string

### WKBReader routines ###
wkb_reader_create = lgeos.GEOSWKBReader_create
wkb_reader_create.restype = WKB_READ_PTR

wkb_reader_destroy = lgeos.GEOSWKBReader_destroy
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

wkb_reader_read = wkb_read_func(lgeos.GEOSWKBReader_read)
wkb_reader_read_hex = wkb_read_func(lgeos.GEOSWKBReader_readHEX)

### WKBWriter routines ###
wkb_writer_create = lgeos.GEOSWKBWriter_create
wkb_writer_create.restype = WKB_WRITE_PTR

wkb_writer_destroy = lgeos.GEOSWKBWriter_destroy
wkb_writer_destroy.argtypes = [WKB_WRITE_PTR]

# WKB Writing prototypes.
def wkb_write_func(func):
    func.argtypes = [WKB_WRITE_PTR, GEOM_PTR, POINTER(c_size_t)]
    func.restype = c_uchar_p
    func.errcheck = check_sized_string
    return func

wkb_writer_write = wkb_write_func(lgeos.GEOSWKBWriter_write)
wkb_writer_write_hex = wkb_write_func(lgeos.GEOSWKBWriter_writeHEX)

# WKBWriter property getter/setter prototypes.
def wkb_writer_get(func, restype=c_int):
    func.argtypes = [WKB_WRITE_PTR]
    func.restype = restype
    return func

def wkb_writer_set(func, argtype=c_int):
    func.argtypes = [WKB_WRITE_PTR, argtype]
    return func

wkb_writer_get_byteorder = wkb_writer_get(lgeos.GEOSWKBWriter_getByteOrder)
wkb_writer_set_byteorder = wkb_writer_set(lgeos.GEOSWKBWriter_setByteOrder)
wkb_writer_get_outdim    = wkb_writer_get(lgeos.GEOSWKBWriter_getOutputDimension)
wkb_writer_set_outdim    = wkb_writer_set(lgeos.GEOSWKBWriter_setOutputDimension)
wkb_writer_get_include_srid = wkb_writer_get(lgeos.GEOSWKBWriter_getIncludeSRID, restype=c_char)
wkb_writer_set_include_srid = wkb_writer_set(lgeos.GEOSWKBWriter_setIncludeSRID, argtype=c_char)
