"""Importer utilities for autodoc"""

from __future__ import annotations

import contextlib
import importlib
import os
import sys
import traceback
import typing
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from sphinx.ext.autodoc.mock import ismock, undecorate
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util import logging
from sphinx.util.inspect import (
    getannotations,
    getmro,
    getslots,
    isclass,
    isenumclass,
    safe_getattr,
)

if TYPE_CHECKING:
    from types import ModuleType

    from sphinx.ext.autodoc import ObjectMember

logger = logging.getLogger(__name__)


def mangle(subject: Any, name: str) -> str:
    """Mangle the given name."""
    try:
        if isclass(subject) and name.startswith('__') and not name.endswith('__'):
            return f"_{subject.__name__}{name}"
    except AttributeError:
        pass

    return name


def unmangle(subject: Any, name: str) -> str | None:
    """Unmangle the given name."""
    try:
        if isclass(subject) and not name.endswith('__'):
            prefix = "_%s__" % subject.__name__
            if name.startswith(prefix):
                return name.replace(prefix, "__", 1)
            else:
                for cls in subject.__mro__:
                    prefix = "_%s__" % cls.__name__
                    if name.startswith(prefix):
                        # mangled attribute defined in parent class
                        return None
    except AttributeError:
        pass

    return name


def import_module(modname: str, warningiserror: bool = False) -> Any:
    """
    Call importlib.import_module(modname), convert exceptions to ImportError
    """
    try:
        with logging.skip_warningiserror(not warningiserror):
            return importlib.import_module(modname)
    except BaseException as exc:
        # Importing modules may cause any side effects, including
        # SystemExit, so we need to catch all errors.
        raise ImportError(exc, traceback.format_exc()) from exc


def _reload_module(module: ModuleType, warningiserror: bool = False) -> Any:
    """
    Call importlib.reload(module), convert exceptions to ImportError
    """
    try:
        with logging.skip_warningiserror(not warningiserror):
            return importlib.reload(module)
    except BaseException as exc:
        # Importing modules may cause any side effects, including
        # SystemExit, so we need to catch all errors.
        raise ImportError(exc, traceback.format_exc()) from exc


def import_object(modname: str, objpath: list[str], objtype: str = '',
                  attrgetter: Callable[[Any, str], Any] = safe_getattr,
                  warningiserror: bool = False) -> Any:
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
                original_module_names = frozenset(sys.modules)
                module = import_module(modname, warningiserror=warningiserror)
                if os.environ.get('SPHINX_AUTODOC_RELOAD_MODULES'):
                    new_modules = [m for m in sys.modules if m not in original_module_names]
                    # Try reloading modules with ``typing.TYPE_CHECKING == True``.
                    try:
                        typing.TYPE_CHECKING = True
                        # Ignore failures; we've already successfully loaded these modules
                        with contextlib.suppress(ImportError, KeyError):
                            for m in new_modules:
                                _reload_module(sys.modules[m])
                    finally:
                        typing.TYPE_CHECKING = False
                    module = sys.modules[modname]
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
            mangled_name = mangle(obj, attrname)
            obj = attrgetter(obj, mangled_name)

            try:
                logger.debug('[autodoc] => %r', obj)
            except TypeError:
                # fallback of failure on logging for broken object
                # refs: https://github.com/sphinx-doc/sphinx/issues/9095
                logger.debug('[autodoc] => %r', (obj,))

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
            errmsg = f'autodoc: failed to import {objtype} {modname!r}'

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

        logger.debug(errmsg)
        raise ImportError(errmsg) from exc


class Attribute(NamedTuple):
    name: str
    directly_defined: bool
    value: Any


def get_object_members(
    subject: Any,
    objpath: list[str],
    attrgetter: Callable,
    analyzer: ModuleAnalyzer | None = None,
) -> dict[str, Attribute]:
    """Get members and attributes of target object."""
    from sphinx.ext.autodoc import INSTANCEATTR

    # the members directly defined in the class
    obj_dict = attrgetter(subject, '__dict__', {})

    members: dict[str, Attribute] = {}

    # enum members
    if isenumclass(subject):
        for name, value in subject.__members__.items():
            if name not in members:
                members[name] = Attribute(name, True, value)

        superclass = subject.__mro__[1]
        for name in obj_dict:
            if name not in superclass.__dict__:
                value = safe_getattr(subject, name)
                members[name] = Attribute(name, True, value)

    # members in __slots__
    try:
        subject___slots__ = getslots(subject)
        if subject___slots__:
            from sphinx.ext.autodoc import SLOTSATTR

            for name in subject___slots__:
                members[name] = Attribute(name, True, SLOTSATTR)
    except (TypeError, ValueError):
        pass

    # other members
    for name in dir(subject):
        try:
            value = attrgetter(subject, name)
            directly_defined = name in obj_dict
            name = unmangle(subject, name)
            if name and name not in members:
                members[name] = Attribute(name, directly_defined, value)
        except AttributeError:
            continue

    # annotation only member (ex. attr: int)
    for i, cls in enumerate(getmro(subject)):
        for name in getannotations(cls):
            name = unmangle(cls, name)
            if name and name not in members:
                members[name] = Attribute(name, i == 0, INSTANCEATTR)

    if analyzer:
        # append instance attributes (cf. self.attr1) if analyzer knows
        namespace = '.'.join(objpath)
        for (ns, name) in analyzer.find_attr_docs():
            if namespace == ns and name not in members:
                members[name] = Attribute(name, True, INSTANCEATTR)

    return members


def get_class_members(subject: Any, objpath: Any, attrgetter: Callable,
                      inherit_docstrings: bool = True) -> dict[str, ObjectMember]:
    """Get members and attributes of target class."""
    from sphinx.ext.autodoc import INSTANCEATTR, ObjectMember

    # the members directly defined in the class
    obj_dict = attrgetter(subject, '__dict__', {})

    members: dict[str, ObjectMember] = {}

    # enum members
    if isenumclass(subject):
        for name, value in subject.__members__.items():
            if name not in members:
                members[name] = ObjectMember(name, value, class_=subject)

        superclass = subject.__mro__[1]
        for name in obj_dict:
            if name not in superclass.__dict__:
                value = safe_getattr(subject, name)
                members[name] = ObjectMember(name, value, class_=subject)

    # members in __slots__
    try:
        subject___slots__ = getslots(subject)
        if subject___slots__:
            from sphinx.ext.autodoc import SLOTSATTR

            for name, docstring in subject___slots__.items():
                members[name] = ObjectMember(name, SLOTSATTR, class_=subject,
                                             docstring=docstring)
    except (TypeError, ValueError):
        pass

    # other members
    for name in dir(subject):
        try:
            value = attrgetter(subject, name)
            if ismock(value):
                value = undecorate(value)

            unmangled = unmangle(subject, name)
            if unmangled and unmangled not in members:
                if name in obj_dict:
                    members[unmangled] = ObjectMember(unmangled, value, class_=subject)
                else:
                    members[unmangled] = ObjectMember(unmangled, value)
        except AttributeError:
            continue

    try:
        for cls in getmro(subject):
            try:
                modname = safe_getattr(cls, '__module__')
                qualname = safe_getattr(cls, '__qualname__')
                analyzer = ModuleAnalyzer.for_module(modname)
                analyzer.analyze()
            except AttributeError:
                qualname = None
                analyzer = None
            except PycodeError:
                analyzer = None

            # annotation only member (ex. attr: int)
            for name in getannotations(cls):
                name = unmangle(cls, name)
                if name and name not in members:
                    if analyzer and (qualname, name) in analyzer.attr_docs:
                        docstring = '\n'.join(analyzer.attr_docs[qualname, name])
                    else:
                        docstring = None

                    members[name] = ObjectMember(name, INSTANCEATTR, class_=cls,
                                                 docstring=docstring)

            # append or complete instance attributes (cf. self.attr1) if analyzer knows
            if analyzer:
                for (ns, name), docstring in analyzer.attr_docs.items():
                    if ns == qualname and name not in members:
                        # otherwise unknown instance attribute
                        members[name] = ObjectMember(name, INSTANCEATTR, class_=cls,
                                                     docstring='\n'.join(docstring))
                    elif (ns == qualname and docstring and
                          isinstance(members[name], ObjectMember) and
                          not members[name].docstring):
                        if cls != subject and not inherit_docstrings:
                            # If we are in the MRO of the class and not the class itself,
                            # and we do not want to inherit docstrings, then skip setting
                            # the docstring below
                            continue
                        # attribute is already known, because dir(subject) enumerates it.
                        # But it has no docstring yet
                        members[name].docstring = '\n'.join(docstring)
    except AttributeError:
        pass

    return members
