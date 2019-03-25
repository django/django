# -*- coding: utf-8 -*-
"""
    sphinx.deprecation
    ~~~~~~~~~~~~~~~~~~

    Sphinx deprecation classes and utilities.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import warnings

if False:
    # For type annotation
    # note: Don't use typing.TYPE_CHECK here (for py27 and py34).
    from typing import Any, Dict, Type  # NOQA


class RemovedInSphinx20Warning(DeprecationWarning):
    pass


class RemovedInSphinx30Warning(PendingDeprecationWarning):
    pass


class RemovedInSphinx40Warning(PendingDeprecationWarning):
    pass


RemovedInNextVersionWarning = RemovedInSphinx20Warning


class DeprecatedDict(dict):
    """A deprecated dict which warns on each access."""

    def __init__(self, data, message, warning):
        # type: (Dict, str, Type[Warning]) -> None
        self.message = message
        self.warning = warning
        super(DeprecatedDict, self).__init__(data)

    def __setitem__(self, key, value):
        # type: (unicode, Any) -> None
        warnings.warn(self.message, self.warning, stacklevel=2)
        super(DeprecatedDict, self).__setitem__(key, value)

    def setdefault(self, key, default=None):
        # type: (unicode, Any) -> None
        warnings.warn(self.message, self.warning, stacklevel=2)
        return super(DeprecatedDict, self).setdefault(key, default)

    def __getitem__(self, key):
        # type: (unicode) -> None
        warnings.warn(self.message, self.warning, stacklevel=2)
        return super(DeprecatedDict, self).__getitem__(key)

    def get(self, key, default=None):
        # type: (unicode, Any) -> None
        warnings.warn(self.message, self.warning, stacklevel=2)
        return super(DeprecatedDict, self).get(key, default)

    def update(self, other=None):  # type: ignore
        # type: (Dict) -> None
        warnings.warn(self.message, self.warning, stacklevel=2)
        super(DeprecatedDict, self).update(other)
