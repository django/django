from ctypes import c_void_p
from types import NoneType
from django.contrib.gis.gdal.error import GDALException

class GDALBase(object):
    """
    Base object for GDAL objects that has a pointer access property
    that controls access to the underlying C pointer.
    """
    # Initially the pointer is NULL.
    _ptr = None

    # Default allowed pointer type.
    ptr_type = c_void_p

    # Pointer access property.
    def _get_ptr(self):
        # Raise an exception if the pointer isn't valid don't
        # want to be passing NULL pointers to routines --
        # that's very bad.
        if self._ptr: return self._ptr
        else: raise GDALException('GDAL %s pointer no longer valid.' % self.__class__.__name__)

    def _set_ptr(self, ptr):
        # Only allow the pointer to be set with pointers of the
        # compatible type or None (NULL).
        if isinstance(ptr, (int, long)):
            self._ptr = self.ptr_type(ptr)
        elif isinstance(ptr, (self.ptr_type, NoneType)):
            self._ptr = ptr
        else:
            raise TypeError('Incompatible pointer type')

    ptr = property(_get_ptr, _set_ptr)

