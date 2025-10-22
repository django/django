"""
This module contains functions that generate ctypes prototypes for the
GDAL routines.
"""

from ctypes import POINTER, c_bool, c_char_p, c_double, c_int, c_int64, c_void_p
from functools import partial

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


def bool_output(func, argtypes, errcheck=None):
    """Generate a ctypes function that returns a boolean value."""
    func.argtypes = argtypes
    func.restype = c_bool
    if errcheck:
        func.errcheck = errcheck
    return func


def double_output(func, argtypes, errcheck=False, strarg=False, cpl=False):
    "Generate a ctypes function that returns a double value."
    func.argtypes = argtypes
    func.restype = c_double
    if errcheck:
        func.errcheck = partial(check_arg_errcode, cpl=cpl)
    if strarg:
        func.errcheck = check_str_arg
    return func


def geom_output(func, argtypes, offset=None):
    """
    Generate a function that returns a Geometry either by reference
    or directly (if the return_geom keyword is set to True).
    """
    # Setting the argument types
    func.argtypes = argtypes

    if not offset:
        # When a geometry pointer is directly returned.
        func.restype = c_void_p
        func.errcheck = check_geom
    else:
        # Error code returned, geometry is returned by-reference.
        func.restype = c_int

        def geomerrcheck(result, func, cargs):
            return check_geom_offset(result, func, cargs, offset)

        func.errcheck = geomerrcheck

    return func


def int_output(func, argtypes, errcheck=None):
    "Generate a ctypes function that returns an integer value."
    func.argtypes = argtypes
    func.restype = c_int
    if errcheck:
        func.errcheck = errcheck
    return func


def int64_output(func, argtypes):
    "Generate a ctypes function that returns a 64-bit integer value."
    func.argtypes = argtypes
    func.restype = c_int64
    return func


def srs_output(func, argtypes):
    """
    Generate a ctypes prototype for the given function with
    the given C arguments that returns a pointer to an OGR
    Spatial Reference System.
    """
    func.argtypes = argtypes
    func.restype = c_void_p
    func.errcheck = check_srs
    return func


def const_string_output(func, argtypes, offset=None, decoding=None, cpl=False):
    func.argtypes = argtypes
    if offset:
        func.restype = c_int
    else:
        func.restype = c_char_p

    def _check_const(result, func, cargs):
        res = check_const_string(result, func, cargs, offset=offset, cpl=cpl)
        if res and decoding:
            res = res.decode(decoding)
        return res

    func.errcheck = _check_const

    return func


def string_output(func, argtypes, offset=-1, str_result=False, decoding=None):
    """
    Generate a ctypes prototype for the given function with the
    given argument types that returns a string from a GDAL pointer.
    The `const` flag indicates whether the allocated pointer should
    be freed via the GDAL library routine VSIFree -- but only applies
    only when `str_result` is True.
    """
    func.argtypes = argtypes
    if str_result:
        # Use subclass of c_char_p so the error checking routine
        # can free the memory at the pointer's address.
        func.restype = gdal_char_p
    else:
        # Error code is returned
        func.restype = c_int

    # Dynamically defining our error-checking function with the
    # given offset.
    def _check_str(result, func, cargs):
        res = check_string(result, func, cargs, offset=offset, str_result=str_result)
        if res and decoding:
            res = res.decode(decoding)
        return res

    func.errcheck = _check_str
    return func


def void_output(func, argtypes, errcheck=True, cpl=False):
    """
    For functions that don't only return an error code that needs to
    be examined.
    """
    if argtypes:
        func.argtypes = argtypes
    if errcheck:
        # `errcheck` keyword may be set to False for routines that
        # return void, rather than a status code.
        func.restype = c_int
        func.errcheck = partial(check_errcode, cpl=cpl)
    else:
        func.restype = None

    return func


def voidptr_output(func, argtypes, errcheck=True):
    "For functions that return c_void_p."
    func.argtypes = argtypes
    func.restype = c_void_p
    if errcheck:
        func.errcheck = check_pointer
    return func


def chararray_output(func, argtypes, errcheck=True):
    """For functions that return a c_char_p array."""
    func.argtypes = argtypes
    func.restype = POINTER(c_char_p)
    if errcheck:
        func.errcheck = check_pointer
    return func
