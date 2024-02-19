from __future__ import annotations

import sys
from collections.abc import Collection, Callable, Sequence
from typing import Any, Protocol, Union, TypeVar, runtime_checkable

from numpy import (
    ndarray,
    dtype,
    generic,
    bool_,
    unsignedinteger,
    integer,
    floating,
    complexfloating,
    number,
    timedelta64,
    datetime64,
    object_,
    void,
    str_,
    bytes_,
)
from ._nested_sequence import _NestedSequence

_T = TypeVar("_T")
_ScalarType = TypeVar("_ScalarType", bound=generic)
_ScalarType_co = TypeVar("_ScalarType_co", bound=generic, covariant=True)
_DType = TypeVar("_DType", bound=dtype[Any])
_DType_co = TypeVar("_DType_co", covariant=True, bound=dtype[Any])

NDArray = ndarray[Any, dtype[_ScalarType_co]]

# The `_SupportsArray` protocol only cares about the default dtype
# (i.e. `dtype=None` or no `dtype` parameter at all) of the to-be returned
# array.
# Concrete implementations of the protocol are responsible for adding
# any and all remaining overloads
@runtime_checkable
class _SupportsArray(Protocol[_DType_co]):
    def __array__(self) -> ndarray[Any, _DType_co]: ...


@runtime_checkable
class _SupportsArrayFunc(Protocol):
    """A protocol class representing `~class.__array_function__`."""
    def __array_function__(
        self,
        func: Callable[..., Any],
        types: Collection[type[Any]],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> object: ...


# TODO: Wait until mypy supports recursive objects in combination with typevars
_FiniteNestedSequence = Union[
    _T,
    Sequence[_T],
    Sequence[Sequence[_T]],
    Sequence[Sequence[Sequence[_T]]],
    Sequence[Sequence[Sequence[Sequence[_T]]]],
]

# A subset of `npt.ArrayLike` that can be parametrized w.r.t. `np.generic`
_ArrayLike = Union[
    _SupportsArray[dtype[_ScalarType]],
    _NestedSequence[_SupportsArray[dtype[_ScalarType]]],
]

# A union representing array-like objects; consists of two typevars:
# One representing types that can be parametrized w.r.t. `np.dtype`
# and another one for the rest
_DualArrayLike = Union[
    _SupportsArray[_DType],
    _NestedSequence[_SupportsArray[_DType]],
    _T,
    _NestedSequence[_T],
]

if sys.version_info >= (3, 12):
    from collections.abc import Buffer

    ArrayLike = Buffer | _DualArrayLike[
        dtype[Any],
        Union[bool, int, float, complex, str, bytes],
    ]
else:
    ArrayLike = _DualArrayLike[
        dtype[Any],
        Union[bool, int, float, complex, str, bytes],
    ]

# `ArrayLike<X>_co`: array-like objects that can be coerced into `X`
# given the casting rules `same_kind`
_ArrayLikeBool_co = _DualArrayLike[
    dtype[bool_],
    bool,
]
_ArrayLikeUInt_co = _DualArrayLike[
    dtype[Union[bool_, unsignedinteger[Any]]],
    bool,
]
_ArrayLikeInt_co = _DualArrayLike[
    dtype[Union[bool_, integer[Any]]],
    Union[bool, int],
]
_ArrayLikeFloat_co = _DualArrayLike[
    dtype[Union[bool_, integer[Any], floating[Any]]],
    Union[bool, int, float],
]
_ArrayLikeComplex_co = _DualArrayLike[
    dtype[Union[
        bool_,
        integer[Any],
        floating[Any],
        complexfloating[Any, Any],
    ]],
    Union[bool, int, float, complex],
]
_ArrayLikeNumber_co = _DualArrayLike[
    dtype[Union[bool_, number[Any]]],
    Union[bool, int, float, complex],
]
_ArrayLikeTD64_co = _DualArrayLike[
    dtype[Union[bool_, integer[Any], timedelta64]],
    Union[bool, int],
]
_ArrayLikeDT64_co = Union[
    _SupportsArray[dtype[datetime64]],
    _NestedSequence[_SupportsArray[dtype[datetime64]]],
]
_ArrayLikeObject_co = Union[
    _SupportsArray[dtype[object_]],
    _NestedSequence[_SupportsArray[dtype[object_]]],
]

_ArrayLikeVoid_co = Union[
    _SupportsArray[dtype[void]],
    _NestedSequence[_SupportsArray[dtype[void]]],
]
_ArrayLikeStr_co = _DualArrayLike[
    dtype[str_],
    str,
]
_ArrayLikeBytes_co = _DualArrayLike[
    dtype[bytes_],
    bytes,
]

_ArrayLikeInt = _DualArrayLike[
    dtype[integer[Any]],
    int,
]

# Extra ArrayLike type so that pyright can deal with NDArray[Any]
# Used as the first overload, should only match NDArray[Any],
# not any actual types.
# https://github.com/numpy/numpy/pull/22193
class _UnknownType:
    ...


_ArrayLikeUnknown = _DualArrayLike[
    dtype[_UnknownType],
    _UnknownType,
]
