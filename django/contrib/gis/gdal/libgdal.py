from __future__ import unicode_literals

import logging
import os
import re
from ctypes import c_char_p, c_int, CDLL, CFUNCTYPE
from ctypes.util import find_library

from django.contrib.gis.gdal.error import OGRException
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger('django.contrib.gis')

# Custom library path set?
try:
    from django.conf import settings
    lib_path = settings.GDAL_LIBRARY_PATH
except (AttributeError, EnvironmentError,
        ImportError, ImproperlyConfigured):
    lib_path = None

if lib_path:
    lib_names = None
elif os.name == 'nt':
    # Windows NT shared libraries
    lib_names = ['gdal19', 'gdal18', 'gdal17', 'gdal16', 'gdal15']
elif os.name == 'posix':
    # *NIX library names.
    lib_names = ['gdal', 'GDAL', 'gdal1.9.0', 'gdal1.8.0', 'gdal1.7.0',
        'gdal1.6.0', 'gdal1.5.0']
else:
    raise OGRException('Unsupported OS "%s"' % os.name)

# Using the ctypes `find_library` utility  to find the
# path to the GDAL library from the list of library names.
if lib_names:
    for lib_name in lib_names:
        lib_path = find_library(lib_name)
        if not lib_path is None: break

if lib_path is None:
    raise OGRException('Could not find the GDAL library (tried "%s"). '
                       'Try setting GDAL_LIBRARY_PATH in your settings.' %
                       '", "'.join(lib_names))

# This loads the GDAL/OGR C library
lgdal = CDLL(lib_path)

# On Windows, the GDAL binaries have some OSR routines exported with
# STDCALL, while others are not.  Thus, the library will also need to
# be loaded up as WinDLL for said OSR functions that require the
# different calling convention.
if os.name == 'nt':
    from ctypes import WinDLL
    lwingdal = WinDLL(lib_path)

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
    return _version_info(b'RELEASE_NAME')

def gdal_full_version():
    "Returns the full GDAL version information."
    return _version_info('')

version_regex = re.compile(r'^(?P<major>\d+)\.(?P<minor>\d+)(\.(?P<subminor>\d+))?')
def gdal_version_info():
    ver = gdal_version().decode()
    m = version_regex.match(ver)
    if not m: raise OGRException('Could not parse GDAL version string "%s"' % ver)
    return dict([(key, m.group(key)) for key in ('major', 'minor', 'subminor')])

_verinfo = gdal_version_info()
GDAL_MAJOR_VERSION = int(_verinfo['major'])
GDAL_MINOR_VERSION = int(_verinfo['minor'])
GDAL_SUBMINOR_VERSION = _verinfo['subminor'] and int(_verinfo['subminor'])
GDAL_VERSION = (GDAL_MAJOR_VERSION, GDAL_MINOR_VERSION, GDAL_SUBMINOR_VERSION)
del _verinfo

# Set library error handling so as errors are logged
CPLErrorHandler = CFUNCTYPE(None, c_int, c_int, c_char_p)
def err_handler(error_class, error_number, message):
    logger.error('GDAL_ERROR %d: %s' % (error_number, message))
err_handler = CPLErrorHandler(err_handler)

def function(name, args, restype):
    func = std_call(name)
    func.argtypes = args
    func.restype = restype
    return func

set_error_handler = function('CPLSetErrorHandler', [CPLErrorHandler], CPLErrorHandler)
set_error_handler(err_handler)
