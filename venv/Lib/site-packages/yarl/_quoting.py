import os
import sys
from typing import TYPE_CHECKING

__all__ = ("_Quoter", "_Unquoter")


NO_EXTENSIONS = bool(os.environ.get("YARL_NO_EXTENSIONS"))  # type: bool
if sys.implementation.name != "cpython":
    NO_EXTENSIONS = True


if TYPE_CHECKING or NO_EXTENSIONS:
    from ._quoting_py import _Quoter, _Unquoter
else:
    try:
        from ._quoting_c import _Quoter, _Unquoter
    except ImportError:  # pragma: no cover
        from ._quoting_py import _Quoter, _Unquoter  # type: ignore[assignment]
