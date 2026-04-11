# cython: language_level=3, freethreading_compatible=True
from types import GenericAlias

from cpython.dict cimport PyDict_GetItem
from cpython.object cimport PyObject


cdef extern from "Python.h":
    # Call a callable Python object callable with exactly
    # 1 positional argument arg and no keyword arguments.
    # Return the result of the call on success, or raise
    # an exception and return NULL on failure.
    PyObject* PyObject_CallOneArg(
        object callable, object arg
    ) except NULL
    int PyDict_SetItem(
        object dict, object key, PyObject* value
    ) except -1
    void Py_DECREF(PyObject*)


cdef class under_cached_property:
    """Use as a class method decorator.  It operates almost exactly like
    the Python `@property` decorator, but it puts the result of the
    method it decorates into the instance dict after the first call,
    effectively replacing the function it decorates with an instance
    variable.  It is, in Python parlance, a data descriptor.

    """

    cdef readonly object wrapped
    cdef object name

    def __init__(self, object wrapped):
        self.wrapped = wrapped
        self.name = wrapped.__name__

    @property
    def __doc__(self):
        return self.wrapped.__doc__

    def __get__(self, object inst, owner):
        if inst is None:
            return self
        cdef dict cache = inst._cache
        cdef PyObject* val = PyDict_GetItem(cache, self.name)
        if val == NULL:
            val = PyObject_CallOneArg(self.wrapped, inst)
            PyDict_SetItem(cache, self.name, val)
            Py_DECREF(val)
        return <object>val

    def __set__(self, inst, value):
        raise AttributeError("cached property is read-only")

    __class_getitem__ = classmethod(GenericAlias)


cdef class cached_property:
    """Use as a class method decorator.  It operates almost exactly like
    the Python `@property` decorator, but it puts the result of the
    method it decorates into the instance dict after the first call,
    effectively replacing the function it decorates with an instance
    variable.  It is, in Python parlance, a data descriptor.

    """

    cdef readonly object func
    cdef object name

    def __init__(self, func):
        self.func = func
        self.name = None

    @property
    def __doc__(self):
        return self.func.__doc__

    def __set_name__(self, owner, object name):
        if self.name is None:
            self.name = name
        elif name != self.name:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self.name!r} and {name!r})."
            )

    def __get__(self, inst, owner):
        if inst is None:
            return self
        if self.name is None:
            raise TypeError(
                "Cannot use cached_property instance"
                " without calling __set_name__ on it.")
        cdef dict cache = inst.__dict__
        cdef PyObject* val = PyDict_GetItem(cache, self.name)
        if val is NULL:
            val = PyObject_CallOneArg(self.func, inst)
            PyDict_SetItem(cache, self.name, val)
            Py_DECREF(val)
        return <object>val

    __class_getitem__ = classmethod(GenericAlias)
