import logging
import os
import re
from ctypes import CDLL, CFUNCTYPE, c_char_p, c_int
from ctypes.util import find_library

from django.contrib.gis.gdal.error import GDALException
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import SimpleLazyObject, lazy

logger = logging.getLogger("django.contrib.gis")


# Set library error handling so as errors are logged
CPLErrorHandler = CFUNCTYPE(None, c_int, c_int, c_char_p)


def err_handler(error_class, error_number, message):
    logger.error("GDAL_ERROR %d: %s", error_number, message)


err_handler = CPLErrorHandler(err_handler)


def load_gdal():
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
            "gdal310",
            "gdal309",
            "gdal308",
            "gdal307",
            "gdal306",
            "gdal305",
            "gdal304",
            "gdal303",
            "gdal302",
            "gdal301",
        ]
    elif os.name == "posix":
        # *NIX library names.
        lib_names = [
            "gdal",
            "GDAL",
            "gdal3.10.0",
            "gdal3.9.0",
            "gdal3.8.0",
            "gdal3.7.0",
            "gdal3.6.0",
            "gdal3.5.0",
            "gdal3.4.0",
            "gdal3.3.0",
            "gdal3.2.0",
            "gdal3.1.0",
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

    # Load the library
    lib = CDLL(lib_path)

    # Set up error handler after library is loaded
    # We do this directly here to avoid circular dependency
    set_error_handler_func = lib["CPLSetErrorHandler"]
    set_error_handler_func.argtypes = [CPLErrorHandler]
    set_error_handler_func.restype = CPLErrorHandler
    set_error_handler_func(err_handler)

    return lib


# This loads the GDAL/OGR C library
lgdal = SimpleLazyObject(load_gdal)


def load_wingdal():
    from ctypes import WinDLL  # type: ignore[attr-defined]

    lib_path = getattr(lgdal, "_name", None)
    return WinDLL(lib_path)


# On Windows, the GDAL binaries have some OSR routines exported with
# STDCALL, while others are not.  Thus, the library will also need to
# be loaded up as WinDLL for said OSR functions that require the
# different calling convention.
if os.name == "nt":
    lwingdal = SimpleLazyObject(load_wingdal)


def std_call(func):
    """
    Return the correct STDCALL function for certain OSR routines on Win32
    platforms.
    """
    if os.name == "nt":
        return lwingdal[func]
    else:
        return lgdal[func]


class GDALFuncFactory:
    """
    Lazy loading of GDAL functions.
    """

    argtypes = None
    restype = None
    errcheck = None

    def __init__(self, func_name, *, restype=None, errcheck=None, argtypes=None):
        self.func_name = func_name
        if restype is not None:
            self.restype = restype
        if errcheck is not None:
            self.errcheck = errcheck
        if argtypes is not None:
            self.argtypes = argtypes

    def __call__(self, *args):
        return self.func(*args)

    @property
    def func(self):
        func = std_call(self.func_name)

        # Setting the argument and return types.
        if self.argtypes is not None:
            func.argtypes = self.argtypes
        if self.restype is not None:
            func.restype = self.restype
        if self.errcheck:
            func.errcheck = self.errcheck
        return func


# #### Version-information functions. ####

# Return GDAL library version information with the given key.
_version_info = GDALFuncFactory(
    "GDALVersionInfo", argtypes=[c_char_p], restype=c_char_p
)


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


GDAL_VERSION = lazy(gdal_version_info, tuple)()
