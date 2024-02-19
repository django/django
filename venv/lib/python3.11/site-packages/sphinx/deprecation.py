"""Sphinx deprecation classes and utilities."""

from __future__ import annotations

import warnings


class RemovedInSphinx80Warning(DeprecationWarning):
    pass


class RemovedInSphinx90Warning(PendingDeprecationWarning):
    pass


RemovedInNextVersionWarning = RemovedInSphinx80Warning


def _deprecation_warning(
    module: str,
    attribute: str,
    canonical_name: str,
    *,
    remove: tuple[int, int],
) -> None:
    """Helper function for module-level deprecations using __getattr__

    Exemplar usage:

    .. code:: python

       # deprecated name -> (object to return, canonical path or empty string)
       _DEPRECATED_OBJECTS = {
           'deprecated_name': (object_to_return, 'fully_qualified_replacement_name', (8, 0)),
       }


       def __getattr__(name):
           if name not in _DEPRECATED_OBJECTS:
               msg = f'module {__name__!r} has no attribute {name!r}'
               raise AttributeError(msg)

           from sphinx.deprecation import _deprecation_warning

           deprecated_object, canonical_name, remove = _DEPRECATED_OBJECTS[name]
           _deprecation_warning(__name__, name, canonical_name, remove=remove)
           return deprecated_object
    """

    if remove == (8, 0):
        warning_class: type[Warning] = RemovedInSphinx80Warning
    elif remove == (9, 0):
        warning_class = RemovedInSphinx90Warning
    else:
        msg = f'removal version {remove!r} is invalid!'
        raise RuntimeError(msg)

    qualified_name = f'{module}.{attribute}'
    if canonical_name:
        message = (f'The alias {qualified_name!r} is deprecated, '
                   f'use {canonical_name!r} instead.')
    else:
        message = f'{qualified_name!r} is deprecated.'

    warnings.warn(message + " Check CHANGES for Sphinx API modifications.",
                  warning_class, stacklevel=3)
