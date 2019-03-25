"""
Python 3 compatibility tools.

"""
from __future__ import division, absolute_import, print_function

__all__ = ['bytes', 'asbytes', 'isfileobj', 'getexception', 'strchar',
           'unicode', 'asunicode', 'asbytes_nested', 'asunicode_nested',
           'asstr', 'open_latin1', 'long', 'basestring', 'sixu',
           'integer_types', 'is_pathlib_path', 'npy_load_module', 'Path',
           'contextlib_nullcontext', 'os_fspath', 'os_PathLike']

import sys
try:
    from pathlib import Path, PurePath
except ImportError:
    Path = PurePath = None

if sys.version_info[0] >= 3:
    import io

    long = int
    integer_types = (int,)
    basestring = str
    unicode = str
    bytes = bytes

    def asunicode(s):
        if isinstance(s, bytes):
            return s.decode('latin1')
        return str(s)

    def asbytes(s):
        if isinstance(s, bytes):
            return s
        return str(s).encode('latin1')

    def asstr(s):
        if isinstance(s, bytes):
            return s.decode('latin1')
        return str(s)

    def isfileobj(f):
        return isinstance(f, (io.FileIO, io.BufferedReader, io.BufferedWriter))

    def open_latin1(filename, mode='r'):
        return open(filename, mode=mode, encoding='iso-8859-1')

    def sixu(s):
        return s

    strchar = 'U'


else:
    bytes = str
    long = long
    basestring = basestring
    unicode = unicode
    integer_types = (int, long)
    asbytes = str
    asstr = str
    strchar = 'S'

    def isfileobj(f):
        return isinstance(f, file)

    def asunicode(s):
        if isinstance(s, unicode):
            return s
        return str(s).decode('ascii')

    def open_latin1(filename, mode='r'):
        return open(filename, mode=mode)

    def sixu(s):
        return unicode(s, 'unicode_escape')


def getexception():
    return sys.exc_info()[1]

def asbytes_nested(x):
    if hasattr(x, '__iter__') and not isinstance(x, (bytes, unicode)):
        return [asbytes_nested(y) for y in x]
    else:
        return asbytes(x)

def asunicode_nested(x):
    if hasattr(x, '__iter__') and not isinstance(x, (bytes, unicode)):
        return [asunicode_nested(y) for y in x]
    else:
        return asunicode(x)

def is_pathlib_path(obj):
    """
    Check whether obj is a pathlib.Path object.

    Prefer using `isinstance(obj, os_PathLike)` instead of this function.
    """
    return Path is not None and isinstance(obj, Path)

# from Python 3.7
class contextlib_nullcontext(object):
    """Context manager that does no additional processing.

    Used as a stand-in for a normal context manager, when a particular
    block of code is only sometimes used with a normal context manager:

    cm = optional_cm if condition else nullcontext()
    with cm:
        # Perform operation, using optional_cm if condition is True
    """

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
        pass


if sys.version_info[0] >= 3 and sys.version_info[1] >= 4:
    def npy_load_module(name, fn, info=None):
        """
        Load a module.

        .. versionadded:: 1.11.2

        Parameters
        ----------
        name : str
            Full module name.
        fn : str
            Path to module file.
        info : tuple, optional
            Only here for backward compatibility with Python 2.*.

        Returns
        -------
        mod : module

        """
        import importlib.machinery
        return importlib.machinery.SourceFileLoader(name, fn).load_module()
else:
    def npy_load_module(name, fn, info=None):
        """
        Load a module.

        .. versionadded:: 1.11.2

        Parameters
        ----------
        name : str
            Full module name.
        fn : str
            Path to module file.
        info : tuple, optional
            Information as returned by `imp.find_module`
            (suffix, mode, type).

        Returns
        -------
        mod : module

        """
        import imp
        import os
        if info is None:
            path = os.path.dirname(fn)
            fo, fn, info = imp.find_module(name, [path])
        else:
            fo = open(fn, info[1])
        try:
            mod = imp.load_module(name, fo, fn, info)
        finally:
            fo.close()
        return mod

# backport abc.ABC
import abc
if sys.version_info[:2] >= (3, 4):
    abc_ABC = abc.ABC
else:
    abc_ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


# Backport os.fs_path, os.PathLike, and PurePath.__fspath__
if sys.version_info[:2] >= (3, 6):
    import os
    os_fspath = os.fspath
    os_PathLike = os.PathLike
else:
    def _PurePath__fspath__(self):
        return str(self)

    class os_PathLike(abc_ABC):
        """Abstract base class for implementing the file system path protocol."""

        @abc.abstractmethod
        def __fspath__(self):
            """Return the file system path representation of the object."""
            raise NotImplementedError

        @classmethod
        def __subclasshook__(cls, subclass):
            if PurePath is not None and issubclass(subclass, PurePath):
                return True
            return hasattr(subclass, '__fspath__')


    def os_fspath(path):
        """Return the path representation of a path-like object.
        If str or bytes is passed in, it is returned unchanged. Otherwise the
        os.PathLike interface is used to get the path representation. If the
        path representation is not str or bytes, TypeError is raised. If the
        provided path is not str, bytes, or os.PathLike, TypeError is raised.
        """
        if isinstance(path, (unicode, bytes)):
            return path

        # Work from the object's type to match method resolution of other magic
        # methods.
        path_type = type(path)
        try:
            path_repr = path_type.__fspath__(path)
        except AttributeError:
            if hasattr(path_type, '__fspath__'):
                raise
            elif PurePath is not None and issubclass(path_type, PurePath):
                return _PurePath__fspath__(path)
            else:
                raise TypeError("expected str, bytes or os.PathLike object, "
                                "not " + path_type.__name__)
        if isinstance(path_repr, (unicode, bytes)):
            return path_repr
        else:
            raise TypeError("expected {}.__fspath__() to return str or bytes, "
                            "not {}".format(path_type.__name__,
                                            type(path_repr).__name__))
