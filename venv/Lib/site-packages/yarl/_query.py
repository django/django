"""Query string handling."""

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, SupportsInt, Union, cast

from multidict import istr

from ._quoters import QUERY_PART_QUOTER, QUERY_QUOTER

SimpleQuery = Union[str, SupportsInt, float]
QueryVariable = Union[SimpleQuery, Sequence[SimpleQuery]]
Query = Union[
    None, str, Mapping[str, QueryVariable], Sequence[tuple[str, QueryVariable]]
]


def query_var(v: SimpleQuery) -> str:
    """Convert a query variable to a string."""
    cls = type(v)
    if cls is int:  # Fast path for non-subclassed int
        return str(v)
    if isinstance(v, str):
        return v
    if isinstance(v, float):
        if math.isinf(v):
            raise ValueError("float('inf') is not supported")
        if math.isnan(v):
            raise ValueError("float('nan') is not supported")
        return str(float(v))
    if cls is not bool and isinstance(v, SupportsInt):
        return str(int(v))
    raise TypeError(
        "Invalid variable type: value "
        "should be str, int or float, got {!r} "
        "of type {}".format(v, cls)
    )


def get_str_query_from_sequence_iterable(
    items: Iterable[tuple[Union[str, istr], QueryVariable]],
) -> str:
    """Return a query string from a sequence of (key, value) pairs.

    value is a single value or a sequence of values for the key

    The sequence of values must be a list or tuple.
    """
    quoter = QUERY_PART_QUOTER
    pairs = [
        f"{quoter(k)}={quoter(v if type(v) is str else query_var(v))}"
        for k, val in items
        for v in (
            val if type(val) is not str and isinstance(val, (list, tuple)) else (val,)
        )
    ]
    return "&".join(pairs)


def get_str_query_from_iterable(
    items: Iterable[tuple[Union[str, istr], SimpleQuery]],
) -> str:
    """Return a query string from an iterable.

    The iterable must contain (key, value) pairs.

    The values are not allowed to be sequences, only single values are
    allowed. For sequences, use `_get_str_query_from_sequence_iterable`.
    """
    quoter = QUERY_PART_QUOTER
    # A listcomp is used since listcomps are inlined on CPython 3.12+ and
    # they are a bit faster than a generator expression.
    pairs = [
        f"{quoter(k)}={quoter(v if type(v) is str else query_var(v))}" for k, v in items
    ]
    return "&".join(pairs)


def get_str_query(*args: Any, **kwargs: Any) -> Union[str, None]:
    """Return a query string from supported args."""
    query: Union[
        str,
        Mapping[str, QueryVariable],
        Sequence[tuple[Union[str, istr], SimpleQuery]],
        None,
    ]
    if kwargs:
        if args:
            msg = "Either kwargs or single query parameter must be present"
            raise ValueError(msg)
        query = kwargs
    elif len(args) == 1:
        query = args[0]
    else:
        raise ValueError("Either kwargs or single query parameter must be present")

    if query is None:
        return None
    if not query:
        return ""
    if type(query) is dict:
        return get_str_query_from_sequence_iterable(query.items())
    if type(query) is str or isinstance(query, str):
        return QUERY_QUOTER(query)
    if isinstance(query, Mapping):
        return get_str_query_from_sequence_iterable(query.items())
    if isinstance(query, (bytes, bytearray, memoryview)):
        msg = "Invalid query type: bytes, bytearray and memoryview are forbidden"
        raise TypeError(msg)
    if isinstance(query, Sequence):
        # We don't expect sequence values if we're given a list of pairs
        # already; only mappings like builtin `dict` which can't have the
        # same key pointing to multiple values are allowed to use
        # `_query_seq_pairs`.
        if TYPE_CHECKING:
            query = cast(Sequence[tuple[Union[str, istr], SimpleQuery]], query)
        return get_str_query_from_iterable(query)
    raise TypeError(
        "Invalid query type: only str, mapping or "
        "sequence of (key, value) pairs is allowed"
    )
