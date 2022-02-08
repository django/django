import logging
import os
import re
from ctypes import CDLL, CFUNCTYPE, c_char_p, c_int
from ctypes.util import find_library

from django.contrib.gis.gdal.error import GDALException
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger("django.contrib.gis")

# Custom library path set?
try:
    from django.conf import settings

    lib_path = settings.GDAL_LIBRARY_PATH
except (AttributeError, ImportError, ImproperlyConfigured, OSError):
    lib_path = None

if lib_path:
    lib_names = None
elif os.name == "nt":
    # Windows NT shared libraries
    lib_names = [
        "gdal303",
        "gdal302",
        "gdal301",
        "gdal300",
        "gdal204",
        "gdal203",
        "gdal202",
        "gdal201",
        "gdal20",
    ]
elif os.name == "posix":
    # *NIX library names.
    lib_names = [
        "gdal",
        "GDAL",
        "gdal3.3.0",
        "gdal3.2.0",
        "gdal3.1.0",
        "gdal3.0.0",
        "gdal2.4.0",
        "gdal2.3.0",
        "gdal2.2.0",
        "gdal2.1.0",
        "gdal2.0.0",
    ]
else:
    raise ImproperlyConfigured('GDAL is unsupported on OS "%s".' % os.name)

# Using the ctypes `find_library` utility  to find the
# path to the GDAL library from the list of library names.
if lib_names:
    for lib_name in lib_names:
        lib_path = find_library(lib_name)
        if lib_path is not None:
            break

if lib_path is None:
    raise ImproperlyConfigured(
        'Could not find the GDAL library (tried "%s"). Is GDAL installed? '
        "If it is, try setting GDAL_LIBRARY_PATH in your settings."
        % '", "'.join(lib_names)
    )

# This loads the GDAL/OGR C library
lgdal = CDLL(lib_path)

# On Windows, the GDAL binaries have some OSR routines exported with
# STDCALL, while others are not.  Thus, the library will also need to
# be loaded up as WinDLL for said OSR functions that require the
# different calling convention.
if os.name == "nt":
    from ctypes import WinDLL

    lwingdal = WinDLL(lib_path)


def std_call(func):
    """
    Return the correct STDCALL function for certain OSR routines on Win32
    platforms.
    """
    if os.name == "nt":
        return lwingdal[func]
    else:
        return lgdal[func]


# #### Version-information functions. ####

# Return GDAL library version information with the given key.
_version_info = std_call("GDALVersionInfo")
_version_info.argtypes = [c_char_p]
_version_info.restype = c_char_p


def gdal_version():
    "Return only the GDAL version number information."
    return _version_info(b"RELEASE_NAME")


def gdal_full_version():
    "Return the full GDAL version information."
    return _version_info(b"")


def gdal_version_info():
    ver = gdal_version()
    m = re.match(rb"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<subminor>\d+))?", ver)
    if not m:
        raise GDALException('Could not parse GDAL version string "%s"' % ver)
    major, minor, subminor = m.groups()
    return (int(major), int(minor), subminor and int(subminor))


GDAL_VERSION = gdal_version_info()

# Set library error handling so as errors are logged
CPLErrorHandler = CFUNCTYPE(None, c_int, c_int, c_char_p)


def err_handler(error_class, error_number, message):
    logger.error("GDAL_ERROR %d: %s", error_number, message)


err_handler = CPLErrorHandler(err_handler)


def function(name, args, restype):
    func = std_call(name)
    func.argtypes = args
    func.restype = restype
    return func


set_error_handler = function("CPLSetErrorHandler", [CPLErrorHandler], CPLErrorHandler)
set_error_handler(err_handler)
