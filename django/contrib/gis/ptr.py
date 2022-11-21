from ctypes import c_void_p


class CPointerBase:
    """
    Base class for objects that have a pointer access property
    that controls access to the underlying C pointer.
    """

    _ptr = None  # Initially the pointer is NULL.
    ptr_type = c_void_p
    destructor = None
    null_ptr_exception_class = AttributeError

    @property
    def ptr(self):
        # Raise an exception if the pointer isn't valid so that NULL pointers
        # aren't passed to routines -- that's very bad.
        if self._ptr:
            return self._ptr
        raise self.null_ptr_exception_class(
            f"NULL {self.__class__.__name__} pointer encountered."
        )

    @ptr.setter
    def ptr(self, ptr):
        # Only allow the pointer to be set with pointers of the compatible
        # type or None (NULL).
        if not (ptr is None or isinstance(ptr, self.ptr_type)):
            raise TypeError(f"Incompatible pointer type: {type(ptr)}.")
        self._ptr = ptr

    def __del__(self):
        """
        Free the memory used by the C++ object.
        """
        if self.destructor and self._ptr:
            try:
                self.destructor(self.ptr)
            except (AttributeError, ImportError, TypeError):
                pass  # Some part might already have been garbage collected
