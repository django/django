from __future__ import annotations

import gc
import sys
from traceback import extract_tb
from typing import TYPE_CHECKING, NoReturn

import pytest

from .._concat_tb import concat_tb

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


def raiser1() -> NoReturn:
    raiser1_2()


def raiser1_2() -> NoReturn:
    raiser1_3()


def raiser1_3() -> NoReturn:
    raise ValueError("raiser1_string")


def raiser2() -> NoReturn:
    raiser2_2()


def raiser2_2() -> NoReturn:
    raise KeyError("raiser2_string")


def get_exc(raiser: Callable[[], NoReturn]) -> Exception:
    try:
        raiser()
    except Exception as exc:
        return exc
    raise AssertionError("raiser should always raise")  # pragma: no cover


def get_tb(raiser: Callable[[], NoReturn]) -> TracebackType | None:
    return get_exc(raiser).__traceback__


def test_concat_tb() -> None:
    tb1 = get_tb(raiser1)
    tb2 = get_tb(raiser2)

    # These return a list of (filename, lineno, fn name, text) tuples
    # https://docs.python.org/3/library/traceback.html#traceback.extract_tb
    entries1 = extract_tb(tb1)
    entries2 = extract_tb(tb2)

    tb12 = concat_tb(tb1, tb2)
    assert extract_tb(tb12) == entries1 + entries2

    tb21 = concat_tb(tb2, tb1)
    assert extract_tb(tb21) == entries2 + entries1

    # Check degenerate cases
    assert extract_tb(concat_tb(None, tb1)) == entries1
    assert extract_tb(concat_tb(tb1, None)) == entries1
    assert concat_tb(None, None) is None

    # Make sure the original tracebacks didn't get mutated by mistake
    assert extract_tb(get_tb(raiser1)) == entries1
    assert extract_tb(get_tb(raiser2)) == entries2


# Unclear if this can still fail, removing the `del` from _concat_tb.copy_tb does not seem
# to trigger it (on a platform where the `del` is executed)
@pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="Only makes sense with refcounting GC",
)
def test_ExceptionGroup_catch_doesnt_create_cyclic_garbage() -> None:
    # https://github.com/python-trio/trio/pull/2063
    gc.collect()
    old_flags = gc.get_debug()

    def make_multi() -> NoReturn:
        raise ExceptionGroup("", [get_exc(raiser1), get_exc(raiser2)])

    try:
        gc.set_debug(gc.DEBUG_SAVEALL)
        with pytest.raises(ExceptionGroup) as excinfo:
            # covers ~~MultiErrorCatcher.__exit__ and~~ _concat_tb.copy_tb
            # TODO: is the above comment true anymore? as this no longer uses MultiError.catch
            raise make_multi()
        for exc in excinfo.value.exceptions:
            assert isinstance(exc, (ValueError, KeyError))
        gc.collect()
        assert not gc.garbage
    finally:
        gc.set_debug(old_flags)
        gc.garbage.clear()
