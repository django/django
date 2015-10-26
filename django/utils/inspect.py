from __future__ import absolute_import

import inspect
import sys

HAS_INSPECT_SIGNATURE = sys.version_info >= (3, 3)


def getargspec(func):
    if not HAS_INSPECT_SIGNATURE:
        return inspect.getargspec(func)

    sig = inspect.signature(func)
    args = [
        p.name for p in sig.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]
    varargs = [
        p.name for p in sig.parameters.values()
        if p.kind == inspect.Parameter.VAR_POSITIONAL
    ]
    varargs = varargs[0] if varargs else None
    varkw = [
        p.name for p in sig.parameters.values()
        if p.kind == inspect.Parameter.VAR_KEYWORD
    ]
    varkw = varkw[0] if varkw else None
    defaults = [
        p.default for p in sig.parameters.values()
        if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD and p.default is not p.empty
    ] or None
    return args, varargs, varkw, defaults


def get_func_args(func):
    if not HAS_INSPECT_SIGNATURE:
        argspec = inspect.getargspec(func)
        return argspec.args[1:]  # ignore 'self'

    sig = inspect.signature(func)
    return [
        arg_name for arg_name, param in sig.parameters.items()
        if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    ]


def func_accepts_kwargs(func):
    if not HAS_INSPECT_SIGNATURE:
        # Not all callables are inspectable with getargspec, so we'll
        # try a couple different ways but in the end fall back on assuming
        # it is -- we don't want to prevent registration of valid but weird
        # callables.
        try:
            argspec = inspect.getargspec(func)
        except TypeError:
            try:
                argspec = inspect.getargspec(func.__call__)
            except (TypeError, AttributeError):
                argspec = None
        return not argspec or argspec[2] is not None

    return any(
        p for p in inspect.signature(func).parameters.values()
        if p.kind == p.VAR_KEYWORD
    )


def func_has_no_args(func):
    args = inspect.getargspec(func)[0] if not HAS_INSPECT_SIGNATURE else [
        p for p in inspect.signature(func).parameters.values()
        if p.kind == p.POSITIONAL_OR_KEYWORD and p.default is p.empty
    ]
    return len(args) == 1


def func_supports_parameter(func, parameter):
    if HAS_INSPECT_SIGNATURE:
        return parameter in inspect.signature(func).parameters
    else:
        args, varargs, varkw, defaults = inspect.getargspec(func)
        return parameter in args
