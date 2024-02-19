"""
    babel.messages
    ~~~~~~~~~~~~~~

    Support for ``gettext`` message catalogs.

    :copyright: (c) 2013-2023 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

from babel.messages.catalog import (
    Catalog,
    Message,
    TranslationError,
)

__all__ = [
    "Catalog",
    "Message",
    "TranslationError",
]
