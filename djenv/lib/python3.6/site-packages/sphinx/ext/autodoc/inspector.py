# -*- coding: utf-8 -*-
"""
    sphinx.ext.autodoc.inspector
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Inspect utilities for autodoc

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import typing
import warnings

from six import StringIO, string_types

from sphinx.deprecation import RemovedInSphinx20Warning
from sphinx.util.inspect import object_description

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Tuple  # NOQA


def format_annotation(annotation):
    # type: (Any) -> str
    """Return formatted representation of a type annotation.

    Show qualified names for types and additional details for types from
    the ``typing`` module.

    Displaying complex types from ``typing`` relies on its private API.
    """
    warnings.warn('format_annotation() is now deprecated.  '
                  'Please use sphinx.util.inspect.Signature instead.',
                  RemovedInSphinx20Warning, stacklevel=2)
    if isinstance(annotation, typing.TypeVar):  # type: ignore
        return annotation.__name__
    if annotation == Ellipsis:
        return '...'
    if not isinstance(annotation, type):
        return repr(annotation)

    qualified_name = (annotation.__module__ + '.' + annotation.__qualname__  # type: ignore
                      if annotation else repr(annotation))

    if annotation.__module__ == 'builtins':
        return annotation.__qualname__  # type: ignore
    else:
        if hasattr(typing, 'GenericMeta') and \
                isinstance(annotation, typing.GenericMeta):
            # In Python 3.5.2+, all arguments are stored in __args__,
            # whereas __parameters__ only contains generic parameters.
            #
            # Prior to Python 3.5.2, __args__ is not available, and all
            # arguments are in __parameters__.
            params = None
            if hasattr(annotation, '__args__'):
                if annotation.__args__ is None or len(annotation.__args__) <= 2:  # type: ignore  # NOQA
                    params = annotation.__args__  # type: ignore
                else:  # typing.Callable
                    args = ', '.join(format_annotation(a) for a in annotation.__args__[:-1])  # type: ignore  # NOQA
                    result = format_annotation(annotation.__args__[-1])  # type: ignore
                    return '%s[[%s], %s]' % (qualified_name, args, result)
            elif hasattr(annotation, '__parameters__'):
                params = annotation.__parameters__  # type: ignore
            if params is not None:
                param_str = ', '.join(format_annotation(p) for p in params)
                return '%s[%s]' % (qualified_name, param_str)
        elif (hasattr(typing, 'UnionMeta') and
              isinstance(annotation, typing.UnionMeta) and  # type: ignore
              hasattr(annotation, '__union_params__')):
            params = annotation.__union_params__
            if params is not None:
                param_str = ', '.join(format_annotation(p) for p in params)
                return '%s[%s]' % (qualified_name, param_str)
        elif (hasattr(typing, 'CallableMeta') and
              isinstance(annotation, typing.CallableMeta) and  # type: ignore
              getattr(annotation, '__args__', None) is not None and
              hasattr(annotation, '__result__')):
            # Skipped in the case of plain typing.Callable
            args = annotation.__args__
            if args is None:
                return qualified_name
            elif args is Ellipsis:
                args_str = '...'
            else:
                formatted_args = (format_annotation(a) for a in args)
                args_str = '[%s]' % ', '.join(formatted_args)
            return '%s[%s, %s]' % (qualified_name,
                                   args_str,
                                   format_annotation(annotation.__result__))
        elif (hasattr(typing, 'TupleMeta') and
              isinstance(annotation, typing.TupleMeta) and  # type: ignore
              hasattr(annotation, '__tuple_params__') and
              hasattr(annotation, '__tuple_use_ellipsis__')):
            params = annotation.__tuple_params__
            if params is not None:
                param_strings = [format_annotation(p) for p in params]
                if annotation.__tuple_use_ellipsis__:
                    param_strings.append('...')
                return '%s[%s]' % (qualified_name,
                                   ', '.join(param_strings))
    return qualified_name


def formatargspec(function, args, varargs=None, varkw=None, defaults=None,
                  kwonlyargs=(), kwonlydefaults={}, annotations={}):
    # type: (Callable, Tuple[str, ...], str, str, Any, Tuple, Dict, Dict[str, Any]) -> str
    """Return a string representation of an ``inspect.FullArgSpec`` tuple.

    An enhanced version of ``inspect.formatargspec()`` that handles typing
    annotations better.
    """
    warnings.warn('formatargspec() is now deprecated.  '
                  'Please use sphinx.util.inspect.Signature instead.',
                  RemovedInSphinx20Warning, stacklevel=2)

    def format_arg_with_annotation(name):
        # type: (str) -> str
        if name in annotations:
            return '%s: %s' % (name, format_annotation(get_annotation(name)))
        return name

    def get_annotation(name):
        # type: (str) -> str
        value = annotations[name]
        if isinstance(value, string_types):
            return introspected_hints.get(name, value)
        else:
            return value

    try:
        introspected_hints = (typing.get_type_hints(function)  # type: ignore
                              if typing and hasattr(function, '__code__') else {})
    except Exception:
        introspected_hints = {}

    fd = StringIO()
    fd.write('(')

    formatted = []
    defaults_start = len(args) - len(defaults) if defaults else len(args)

    for i, arg in enumerate(args):
        arg_fd = StringIO()
        if isinstance(arg, list):
            # support tupled arguments list (only for py2): def foo((x, y))
            arg_fd.write('(')
            arg_fd.write(format_arg_with_annotation(arg[0]))
            for param in arg[1:]:
                arg_fd.write(', ')
                arg_fd.write(format_arg_with_annotation(param))
            arg_fd.write(')')
        else:
            arg_fd.write(format_arg_with_annotation(arg))
            if defaults and i >= defaults_start:
                arg_fd.write(' = ' if arg in annotations else '=')
                arg_fd.write(object_description(defaults[i - defaults_start]))  # type: ignore
        formatted.append(arg_fd.getvalue())

    if varargs:
        formatted.append('*' + format_arg_with_annotation(varargs))

    if kwonlyargs:
        if not varargs:
            formatted.append('*')

        for kwarg in kwonlyargs:
            arg_fd = StringIO()
            arg_fd.write(format_arg_with_annotation(kwarg))
            if kwonlydefaults and kwarg in kwonlydefaults:
                arg_fd.write(' = ' if kwarg in annotations else '=')
                arg_fd.write(object_description(kwonlydefaults[kwarg]))  # type: ignore
            formatted.append(arg_fd.getvalue())

    if varkw:
        formatted.append('**' + format_arg_with_annotation(varkw))

    fd.write(', '.join(formatted))
    fd.write(')')

    if 'return' in annotations:
        fd.write(' -> ')
        fd.write(format_annotation(get_annotation('return')))

    return fd.getvalue()
