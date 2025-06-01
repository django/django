"""
This module contains functions that generate ctypes prototypes for the
GDAL routines.
"""

from ctypes import POINTER, c_bool, c_char_p, c_double, c_int, c_int64, c_void_p
from functools import partial

from django.contrib.gis.gdal.libgdal import GDALFuncFactory
from django.contrib.gis.gdal.prototypes.errcheck import (
    check_arg_errcode,
    check_const_string,
    check_errcode,
    check_geom,
    check_geom_offset,
    check_pointer,
    check_srs,
    check_str_arg,
    check_string,
)


class gdal_char_p(c_char_p):
    pass


class BoolOutput(GDALFuncFactory):
    """Generate a ctypes function that returns a boolean value."""

    restype = c_bool


class DoubleOutput(GDALFuncFactory):
    """Generate a ctypes function that returns a double value."""

    restype = c_double

    def __init__(self, func_name, *, errcheck=False, strarg=False, cpl=False, **kwargs):
        super().__init__(func_name, **kwargs)
        if strarg:
            self.errcheck = staticmethod(check_str_arg)
        elif errcheck:
            self.errcheck = staticmethod(partial(check_arg_errcode, cpl=cpl))


class GeomOutput(GDALFuncFactory):
    """
    Generate a function that returns a Geometry either by reference
    or directly (if the return_geom keyword is set to True).
    """

    def __init__(self, func_name, *, offset=None, **kwargs):
        super().__init__(func_name, **kwargs)
        if not offset:
            # When a geometry pointer is directly returned.
            self.restype = c_void_p
            self.errcheck = staticmethod(check_geom)
        else:
            # Error code returned, geometry is returned by-reference.
            self.restype = c_int

            def geomerrcheck(result, func, cargs):
                return check_geom_offset(result, func, cargs, offset)

            self.errcheck = staticmethod(geomerrcheck)


class IntOutput(GDALFuncFactory):
    """Generate a ctypes function that returns an integer value."""

    restype = c_int


class Int64Output(GDALFuncFactory):
    """Generate a ctypes function that returns a 64-bit integer value."""

    restype = c_int64


class SRSOutput(GDALFuncFactory):
    """
    Generate a ctypes prototype for the given function with
    the given C arguments that returns a pointer to an OGR
    Spatial Reference System.
    """

    restype = c_void_p
    errcheck = staticmethod(check_srs)


class ConstStringOutput(GDALFuncFactory):
    def __init__(self, func_name, *, offset=None, decoding=None, cpl=False, **kwargs):
        super().__init__(func_name, **kwargs)
        if offset:
            self.restype = c_int
        else:
            self.restype = c_char_p

        def _check_const(result, func, cargs):
            res = check_const_string(result, func, cargs, offset=offset, cpl=cpl)
            if res and decoding:
                res = res.decode(decoding)
            return res

        self.errcheck = staticmethod(_check_const)


class StringOutput(GDALFuncFactory):
    """
    Generate a ctypes prototype for the given function with the
    given argument types that returns a string from a GDAL pointer.
    The `const` flag indicates whether the allocated pointer should
    be freed via the GDAL library routine VSIFree -- but only applies
    only when `str_result` is True.
    """

    def __init__(
        self, func_name, *, offset=-1, str_result=False, decoding=None, **kwargs
    ):
        super().__init__(func_name, **kwargs)
        if str_result:
            # Use subclass of c_char_p so the error checking routine
            # can free the memory at the pointer's address.
            self.restype = gdal_char_p
        else:
            # Error code is returned
            self.restype = c_int

        # Dynamically defining our error-checking function with the
        # given offset.
        def _check_str(result, func, cargs):
            res = check_string(
                result, func, cargs, offset=offset, str_result=str_result
            )
            if res and decoding:
                res = res.decode(decoding)
            return res

        self.errcheck = staticmethod(_check_str)


class VoidOutput(GDALFuncFactory):
    """
    For functions that don't only return an error code that needs to
    be examined.
    """

    def __init__(self, func_name, *, errcheck=True, cpl=False, **kwargs):
        super().__init__(func_name, **kwargs)
        if errcheck:
            # `errcheck` keyword may be set to False for routines that
            # return void, rather than a status code.
            self.restype = c_int
            self.errcheck = staticmethod(partial(check_errcode, cpl=cpl))
        else:
            self.restype = None
            self.errcheck = None


class VoidPtrOutput(GDALFuncFactory):
    """For functions that return c_void_p."""

    restype = c_void_p

    def __init__(self, func_name, *, errcheck=True, **kwargs):
        super().__init__(func_name, **kwargs)
        if errcheck:
            self.errcheck = staticmethod(check_pointer)
        else:
            self.errcheck = None


class CharArrayOutput(GDALFuncFactory):
    """For functions that return a c_char_p array."""

    restype = POINTER(c_char_p)

    def __init__(self, func_name, *, errcheck=True, **kwargs):
        super().__init__(func_name, **kwargs)
        if errcheck:
            self.errcheck = staticmethod(check_pointer)
        else:
            self.errcheck = None
