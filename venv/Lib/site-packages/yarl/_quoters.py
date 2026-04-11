"""Quoting and unquoting utilities for URL parts."""

from typing import Union
from urllib.parse import quote

from ._quoting import _Quoter, _Unquoter

QUOTER = _Quoter(requote=False)
REQUOTER = _Quoter()
PATH_QUOTER = _Quoter(safe="@:", protected="/+", requote=False)
PATH_REQUOTER = _Quoter(safe="@:", protected="/+")
QUERY_QUOTER = _Quoter(safe="?/:@", protected="=+&;", qs=True, requote=False)
QUERY_REQUOTER = _Quoter(safe="?/:@", protected="=+&;", qs=True)
QUERY_PART_QUOTER = _Quoter(safe="?/:@", qs=True, requote=False)
FRAGMENT_QUOTER = _Quoter(safe="?/:@", requote=False)
FRAGMENT_REQUOTER = _Quoter(safe="?/:@")

UNQUOTER = _Unquoter()
PATH_UNQUOTER = _Unquoter(unsafe="+")
PATH_SAFE_UNQUOTER = _Unquoter(ignore="/%", unsafe="+")
QS_UNQUOTER = _Unquoter(qs=True)
UNQUOTER_PLUS = _Unquoter(plus=True)  # to match urllib.parse.unquote_plus


def human_quote(s: Union[str, None], unsafe: str) -> Union[str, None]:
    if not s:
        return s
    for c in "%" + unsafe:
        if c in s:
            s = s.replace(c, f"%{ord(c):02X}")
    if s.isprintable():
        return s
    return "".join(c if c.isprintable() else quote(c) for c in s)
