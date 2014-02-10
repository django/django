from ctypes import c_char_p, c_float, c_int, string_at, Structure, POINTER
from django.contrib.gis.geoip.libgeoip import lgeoip, free

#### GeoIP C Structure definitions ####

class GeoIPRecord(Structure):
    _fields_ = [('country_code', c_char_p),
                ('country_code3', c_char_p),
                ('country_name', c_char_p),
                ('region', c_char_p),
                ('city', c_char_p),
                ('postal_code', c_char_p),
                ('latitude', c_float),
                ('longitude', c_float),
                # TODO: In 1.4.6 this changed from `int dma_code;` to
                # `union {int metro_code; int dma_code;};`.  Change
                # to a `ctypes.Union` in to accomodate in future when
                # pre-1.4.6 versions are no longer distributed.
                ('dma_code', c_int),
                ('area_code', c_int),
                ('charset', c_int),
                ('continent_code', c_char_p),
                ]
geoip_char_fields = [name for name, ctype in GeoIPRecord._fields_ if ctype is c_char_p]
GEOIP_DEFAULT_ENCODING = 'iso-8859-1'
geoip_encodings = { 0: 'iso-8859-1',
                    1: 'utf8',
                    }

class GeoIPTag(Structure): pass

RECTYPE = POINTER(GeoIPRecord)
DBTYPE = POINTER(GeoIPTag)

#### ctypes function prototypes ####

# GeoIP_lib_version appeared in version 1.4.7.
if hasattr(lgeoip, 'GeoIP_lib_version'):
    GeoIP_lib_version = lgeoip.GeoIP_lib_version
    GeoIP_lib_version.argtypes = None
    GeoIP_lib_version.restype = c_char_p
else:
    GeoIP_lib_version = None

# For freeing memory allocated within a record
GeoIPRecord_delete = lgeoip.GeoIPRecord_delete
GeoIPRecord_delete.argtypes = [RECTYPE]
GeoIPRecord_delete.restype = None

# For retrieving records by name or address.
def check_record(result, func, cargs):
    if bool(result):
        # Checking the pointer to the C structure, if valid pull out elements
        # into a dicionary.
        rec = result.contents
        record = dict((fld, getattr(rec, fld)) for fld, ctype in rec._fields_)

        # Now converting the strings to unicode using the proper encoding.
        encoding = geoip_encodings[record['charset']]
        for char_field in geoip_char_fields:
            if record[char_field]:
                record[char_field] = record[char_field].decode(encoding)

        # Free the memory allocated for the struct & return.
        GeoIPRecord_delete(result)
        return record
    else:
        return None

def record_output(func):
    func.argtypes = [DBTYPE, c_char_p]
    func.restype = RECTYPE
    func.errcheck = check_record
    return func
GeoIP_record_by_addr = record_output(lgeoip.GeoIP_record_by_addr)
GeoIP_record_by_name = record_output(lgeoip.GeoIP_record_by_name)


# For opening & closing GeoIP database files.
GeoIP_open = lgeoip.GeoIP_open
GeoIP_open.restype = DBTYPE
GeoIP_delete = lgeoip.GeoIP_delete
GeoIP_delete.argtypes = [DBTYPE]
GeoIP_delete.restype = None

# This is so the string pointer can be freed within Python.
class geoip_char_p(c_char_p):
    pass

def check_string(result, func, cargs):
    if result:
        s = string_at(result)
        free(result)
    else:
        s = ''
    return s.decode(GEOIP_DEFAULT_ENCODING)

GeoIP_database_info = lgeoip.GeoIP_database_info
GeoIP_database_info.restype = geoip_char_p
GeoIP_database_info.errcheck = check_string

# String output routines.
def string_output(func):
    def _err_check(result, func, cargs):
        if result:
            return result.decode(GEOIP_DEFAULT_ENCODING)
        return result
    func.restype = c_char_p
    func.errcheck = _err_check
    return func

GeoIP_country_code_by_addr = string_output(lgeoip.GeoIP_country_code_by_addr)
GeoIP_country_code_by_name = string_output(lgeoip.GeoIP_country_code_by_name)
GeoIP_country_name_by_addr = string_output(lgeoip.GeoIP_country_name_by_addr)
GeoIP_country_name_by_name = string_output(lgeoip.GeoIP_country_name_by_name)
