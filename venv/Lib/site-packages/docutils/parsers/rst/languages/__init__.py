# $Id: __init__.py 10046 2025-03-09 01:45:28Z aa-turner $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# Internationalization details are documented in
# <https://docutils.sourceforge.io/docs/howto/i18n.html>.

"""
This package contains modules for language-dependent features of
reStructuredText.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils.languages import LanguageImporter

TYPE_CHECKING = False
if TYPE_CHECKING:
    import types
    from typing import NoReturn, Protocol, overload

    class RSTLanguageModule(Protocol):
        __name__: str

        directives: dict[str, str]
        roles: dict[str, str]
else:
    from docutils.utils._typing import overload


class RstLanguageImporter(LanguageImporter):
    """Import language modules.

    When called with a BCP 47 language tag, instances return a module
    with localisations for "directive" and "role" names for  from
    `docutils.parsers.rst.languages` or the PYTHONPATH.

    If there is no matching module, warn (if a `reporter` is passed)
    and return None.
    """
    packages = ('docutils.parsers.rst.languages.', '')
    warn_msg = 'rST localisation for language "%s" not found.'
    fallback = None

    @overload
    def check_content(self, module: RSTLanguageModule) -> None:
        ...

    @overload
    def check_content(self, module: types.ModuleType) -> NoReturn:
        ...

    def check_content(self, module: RSTLanguageModule | types.ModuleType
                      ) -> None:
        """Check if we got an rST language module."""
        if not (isinstance(module.directives, dict)
                and isinstance(module.roles, dict)):
            raise ImportError


get_language: LanguageImporter[RSTLanguageModule] = RstLanguageImporter()
