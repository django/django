# SPDX-License-Identifier: MIT

from attr import (
    NOTHING,
    Attribute,
    AttrsInstance,
    Converter,
    Factory,
    NothingType,
    _make_getattr,
    assoc,
    cmp_using,
    define,
    evolve,
    field,
    fields,
    fields_dict,
    frozen,
    has,
    make_class,
    mutable,
    resolve_types,
    validate,
)
from attr._make import ClassProps
from attr._next_gen import asdict, astuple, inspect

from . import converters, exceptions, filters, setters, validators


__all__ = [
    "NOTHING",
    "Attribute",
    "AttrsInstance",
    "ClassProps",
    "Converter",
    "Factory",
    "NothingType",
    "__author__",
    "__copyright__",
    "__description__",
    "__doc__",
    "__email__",
    "__license__",
    "__title__",
    "__url__",
    "__version__",
    "__version_info__",
    "asdict",
    "assoc",
    "astuple",
    "cmp_using",
    "converters",
    "define",
    "evolve",
    "exceptions",
    "field",
    "fields",
    "fields_dict",
    "filters",
    "frozen",
    "has",
    "inspect",
    "make_class",
    "mutable",
    "resolve_types",
    "setters",
    "validate",
    "validators",
]

__getattr__ = _make_getattr(__name__)
