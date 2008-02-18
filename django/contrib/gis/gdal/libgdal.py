import os, sys
from ctypes import c_char_p, CDLL
from ctypes.util import find_library
from django.contrib.gis.gdal.error import OGRException

# Custom library path set?
try:
    from django.conf import settings
    lib_name = settings.GDAL_LIBRARY_PATH
except (AttributeError, EnvironmentError, ImportError):
    lib_name = None

if lib_name:
    pass
elif os.name == 'nt':
    # Windows NT shared library
    lib_name = 'gdal15.dll'
elif os.name == 'posix':
    platform = os.uname()[0]
    if platform == 'Darwin':
        # Mac OSX shared library
        lib_name = 'libgdal.dylib'
    else: 
        # Attempting to use .so extension for all other platforms.
        lib_name = 'libgdal.so'
else:
    raise OGRException('Unsupported OS "%s"' % os.name)

# This loads the GDAL/OGR C library
lgdal = CDLL(lib_name)

# On Windows, the GDAL binaries have some OSR routines exported with 
# STDCALL, while others are not.  Thus, the library will also need to 
# be loaded up as WinDLL for said OSR functions that require the 
# different calling convention.
if os.name == 'nt':
    from ctypes import WinDLL
    lwingdal = WinDLL(lib_name)

def std_call(func):
    """
    Returns the correct STDCALL function for certain OSR routines on Win32
    platforms.
    """
    if os.name == 'nt':
        return lwingdal[func]
    else:
        return lgdal[func]

#### Version-information functions. ####

# Returns GDAL library version information with the given key.
_version_info = std_call('GDALVersionInfo')
_version_info.argtypes = [c_char_p]
_version_info.restype = c_char_p

def gdal_version():
    "Returns only the GDAL version number information."
    return _version_info('RELEASE_NAME')

def gdal_full_version(): 
    "Returns the full GDAL version information."
    return _version_info('')

def gdal_release_date(date=False): 
    """
    Returns the release date in a string format, e.g, "2007/06/27".
    If the date keyword argument is set to True, a Python datetime object
    will be returned instead.
    """
    from datetime import date as date_type
    rel = _version_info('RELEASE_DATE')
    yy, mm, dd = map(int, (rel[0:4], rel[4:6], rel[6:8]))
    d = date_type(yy, mm, dd)
    if date: return d
    else: return d.strftime('%Y/%m/%d')
