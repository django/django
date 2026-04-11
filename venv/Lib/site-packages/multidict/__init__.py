"""
Multidict implementation.

HTTP Headers and URL query string require specific data structure:
multidict. It behaves mostly like a dict but it can have
several values for the same key.
"""

from typing import TYPE_CHECKING

from ._abc import MultiMapping, MutableMultiMapping
from ._compat import USE_EXTENSIONS

__all__ = (
    "CIMultiDict",
    "CIMultiDictProxy",
    "MultiDict",
    "MultiDictProxy",
    "MultiMapping",
    "MutableMultiMapping",
    "getversion",
    "istr",
    "upstr",
)

__version__ = "6.7.1"


if TYPE_CHECKING or not USE_EXTENSIONS:
    from ._multidict_py import (
        CIMultiDict,
        CIMultiDictProxy,
        MultiDict,
        MultiDictProxy,
        getversion,
        istr,
    )
else:
    from collections.abc import ItemsView, KeysView, ValuesView

    from ._multidict import (
        CIMultiDict,
        CIMultiDictProxy,
        MultiDict,
        MultiDictProxy,
        _ItemsView,
        _KeysView,
        _ValuesView,
        getversion,
        istr,
    )

    MultiMapping.register(MultiDictProxy)
    MutableMultiMapping.register(MultiDict)
    KeysView.register(_KeysView)
    ItemsView.register(_ItemsView)
    ValuesView.register(_ValuesView)


upstr = istr
