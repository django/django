# -*- coding: utf-8 -*-
"""
    sphinx.ext.autodoc.importer
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Importer utilities for autodoc

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import contextlib
import sys
import traceback
import warnings
from collections import namedtuple
from types import FunctionType, MethodType, ModuleType

from six import PY2, iteritems

from sphinx.util import logging
from sphinx.util.inspect import isenumclass, safe_getattr

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Tuple  # NOQA

logger = logging.getLogger(__name__)


class _MockObject(object):
    """Used by autodoc_mock_imports."""

    def __new__(cls, *args, **kwargs):
        # type: (Any, Any) -> Any
        if len(args) == 3 and isinstance(args[1], tuple) and args[1][-1].__class__ is cls:
            # subclassing MockObject
            return type(args[0], (_MockObject,), args[2], **kwargs)  # type: ignore
        else:
            return super(_MockObject, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        self.__qualname__ = ''

    def __len__(self):
        # type: () -> int
        return 0

    def __contains__(self, key):
        # type: (str) -> bool
        return False

    def __iter__(self):
        # type: () -> Iterator
        return iter([])

    def __mro_entries__(self, bases):
        # type: (Tuple) -> Tuple
        return (self.__class__,)

    def __getitem__(self, key):
        # type: (str) -> _MockObject
        return self

    def __getattr__(self, key):
        # type: (str) -> _MockObject
        return self

    def __call__(self, *args, **kw):
        # type: (Any, Any) -> Any
        if args and type(args[0]) in [FunctionType, MethodType]:
            # Appears to be a decorator, pass through unchanged
            return args[0]
        return self


class _MockModule(ModuleType):
    """Used by autodoc_mock_imports."""
    __file__ = '/dev/null'

    def __init__(self, name, loader):
        # type: (str, _MockImporter) -> None
        self.__name__ = self.__package__ = name
        self.__loader__ = loader
        self.__all__ = []  # type: List[str]
        self.__path__ = []  # type: List[str]

    def __getattr__(self, name):
        # type: (str) -> _MockObject
        o = _MockObject()
        o.__module__ = self.__name__
        return o


class _MockImporter(object):
    def __init__(self, names):
        # type: (List[str]) -> None
        self.names = names
        self.mocked_modules = []  # type: List[str]
        # enable hook by adding itself to meta_path
        sys.meta_path.insert(0, self)

    def disable(self):
        # type: () -> None
        # remove `self` from `sys.meta_path` to disable import hook
        sys.meta_path = [i for i in sys.meta_path if i is not self]
        # remove mocked modules from sys.modules to avoid side effects after
        # running auto-documenter
        for m in self.mocked_modules:
            if m in sys.modules:
                del sys.modules[m]

    def find_module(self, name, path=None):
        # type: (str, str) -> Any
        # check if name is (or is a descendant of) one of our base_packages
        for n in self.names:
            if n == name or name.startswith(n + '.'):
                return self
        return None

    def load_module(self, name):
        # type: (str) -> ModuleType
        if name in sys.modules:
            # module has already been imported, return it
            return sys.modules[name]
        else:
            logger.debug('[autodoc] adding a mock module %s!', name)
            module = _MockModule(name, self)
            sys.modules[name] = module
            self.mocked_modules.append(name)
            return module


@contextlib.contextmanager
def mock(names):
    # type: (List[str]) -> Generator
    try:
        importer = _MockImporter(names)
        yield
    finally:
        importer.disable()


def import_module(modname, warningiserror=False):
    # type: (str, bool) -> Any
    """
    Call __import__(modname), convert exceptions to ImportError
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ImportWarning)
            with logging.skip_warningiserror(not warningiserror):
                __import__(modname)
                return sys.modules[modname]
    except BaseException as exc:
        # Importing modules may cause any side effects, including
        # SystemExit, so we need to catch all errors.
        raise ImportError(exc, traceback.format_exc())


def import_object(modname, objpath, objtype='', attrgetter=safe_getattr, warningiserror=False):
    # type: (str, List[unicode], str, Callable[[Any, unicode], Any], bool) -> Any
    if objpath:
        logger.debug('[autodoc] from %s import %s', modname, '.'.join(objpath))
    else:
        logger.debug('[autodoc] import %s', modname)

    try:
        module = None
        exc_on_importing = None
        objpath = list(objpath)
        while module is None:
            try:
                module = import_module(modname, warningiserror=warningiserror)
                logger.debug('[autodoc] import %s => %r', modname, module)
            except ImportError as exc:
                logger.debug('[autodoc] import %s => failed', modname)
                exc_on_importing = exc
                if '.' in modname:
                    # retry with parent module
                    modname, name = modname.rsplit('.', 1)
                    objpath.insert(0, name)
                else:
                    raise

        obj = module
        parent = None
        object_name = None
        for attrname in objpath:
            parent = obj
            logger.debug('[autodoc] getattr(_, %r)', attrname)
            obj = attrgetter(obj, attrname)
            logger.debug('[autodoc] => %r', obj)
            object_name = attrname
        return [module, parent, object_name, obj]
    except (AttributeError, ImportError) as exc:
        if isinstance(exc, AttributeError) and exc_on_importing:
            # restore ImportError
            exc = exc_on_importing

        if objpath:
            errmsg = ('autodoc: failed to import %s %r from module %r' %
                      (objtype, '.'.join(objpath), modname))
        else:
            errmsg = 'autodoc: failed to import %s %r' % (objtype, modname)

        if isinstance(exc, ImportError):
            # import_module() raises ImportError having real exception obj and
            # traceback
            real_exc, traceback_msg = exc.args
            if isinstance(real_exc, SystemExit):
                errmsg += ('; the module executes module level statement '
                           'and it might call sys.exit().')
            elif isinstance(real_exc, ImportError) and real_exc.args:
                errmsg += '; the following exception was raised:\n%s' % real_exc.args[0]
            else:
                errmsg += '; the following exception was raised:\n%s' % traceback_msg
        else:
            errmsg += '; the following exception was raised:\n%s' % traceback.format_exc()

        if PY2:
            errmsg = errmsg.decode('utf-8')  # type: ignore
        logger.debug(errmsg)
        raise ImportError(errmsg)


Attribute = namedtuple('Attribute', ['name', 'directly_defined', 'value'])


def get_object_members(subject, objpath, attrgetter, analyzer=None):
    # type: (Any, List[unicode], Callable, Any) -> Dict[str, Attribute]  # NOQA
    """Get members and attributes of target object."""
    # the members directly defined in the class
    obj_dict = attrgetter(subject, '__dict__', {})

    # Py34 doesn't have enum members in __dict__.
    if sys.version_info[:2] == (3, 4) and isenumclass(subject):
        obj_dict = dict(obj_dict)
        for name, value in subject.__members__.items():
            obj_dict[name] = value

    members = {}  # type: Dict[str, Attribute]

    # enum members
    if isenumclass(subject):
        for name, value in subject.__members__.items():
            if name not in members:
                members[name] = Attribute(name, True, value)

        superclass = subject.__mro__[1]
        for name, value in iteritems(obj_dict):
            if name not in superclass.__dict__:
                members[name] = Attribute(name, True, value)

    # other members
    for name in dir(subject):
        try:
            value = attrgetter(subject, name)
            directly_defined = name in obj_dict
            if name not in members:
                members[name] = Attribute(name, directly_defined, value)
        except AttributeError:
            continue

    if analyzer:
        # append instance attributes (cf. self.attr1) if analyzer knows
        from sphinx.ext.autodoc import INSTANCEATTR

        namespace = '.'.join(objpath)
        for (ns, name) in analyzer.find_attr_docs():
            if namespace == ns and name not in members:
                members[name] = Attribute(name, True, INSTANCEATTR)

    return members
