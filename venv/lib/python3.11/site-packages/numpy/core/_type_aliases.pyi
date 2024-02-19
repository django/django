from typing import Any, TypedDict

from numpy import generic, signedinteger, unsignedinteger, floating, complexfloating

class _SCTypes(TypedDict):
    int: list[type[signedinteger[Any]]]
    uint: list[type[unsignedinteger[Any]]]
    float: list[type[floating[Any]]]
    complex: list[type[complexfloating[Any, Any]]]
    others: list[type]

sctypeDict: dict[int | str, type[generic]]
sctypes: _SCTypes
