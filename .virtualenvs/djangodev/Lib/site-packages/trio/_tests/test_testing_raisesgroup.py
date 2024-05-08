from __future__ import annotations

import re
import sys
from types import TracebackType
from typing import Any

import pytest

import trio
from trio.testing import Matcher, RaisesGroup

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


def wrap_escape(s: str) -> str:
    return "^" + re.escape(s) + "$"


def test_raises_group() -> None:
    with pytest.raises(
        ValueError,
        match=wrap_escape(
            f'Invalid argument "{TypeError()!r}" must be exception type, Matcher, or RaisesGroup.'
        ),
    ):
        RaisesGroup(TypeError())

    with RaisesGroup(ValueError):
        raise ExceptionGroup("foo", (ValueError(),))

    with RaisesGroup(SyntaxError):
        with RaisesGroup(ValueError):
            raise ExceptionGroup("foo", (SyntaxError(),))

    # multiple exceptions
    with RaisesGroup(ValueError, SyntaxError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # order doesn't matter
    with RaisesGroup(SyntaxError, ValueError):
        raise ExceptionGroup("foo", (ValueError(), SyntaxError()))

    # nested exceptions
    with RaisesGroup(RaisesGroup(ValueError)):
        raise ExceptionGroup("foo", (ExceptionGroup("bar", (ValueError(),)),))

    with RaisesGroup(
        SyntaxError,
        RaisesGroup(ValueError),
        RaisesGroup(RuntimeError),
    ):
        raise ExceptionGroup(
            "foo",
            (
                SyntaxError(),
                ExceptionGroup("bar", (ValueError(),)),
                ExceptionGroup("", (RuntimeError(),)),
            ),
        )

    # will error if there's excess exceptions
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError):
            raise ExceptionGroup("", (ValueError(), ValueError()))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError):
            raise ExceptionGroup("", (RuntimeError(), ValueError()))

    # will error if there's missing exceptions
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, ValueError):
            raise ExceptionGroup("", (ValueError(),))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, SyntaxError):
            raise ExceptionGroup("", (ValueError(),))

    # loose semantics, as with expect*
    with RaisesGroup(ValueError, strict=False):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

    # mixed loose is possible if you want it to be at least N deep
    with RaisesGroup(RaisesGroup(ValueError, strict=False)):
        raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))
    with RaisesGroup(RaisesGroup(ValueError, strict=False)):
        raise ExceptionGroup(
            "", (ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),)),)
        )
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(RaisesGroup(ValueError, strict=False)):
            raise ExceptionGroup("", (ValueError(),))

    # but not the other way around
    with pytest.raises(
        ValueError,
        match="^You cannot specify a nested structure inside a RaisesGroup with strict=False$",
    ):
        RaisesGroup(RaisesGroup(ValueError), strict=False)

    # currently not fully identical in behaviour to expect*, which would also catch an unwrapped exception
    with pytest.raises(ValueError, match="^value error text$"):
        with RaisesGroup(ValueError, strict=False):
            raise ValueError("value error text")


def test_match() -> None:
    # supports match string
    with RaisesGroup(ValueError, match="bar"):
        raise ExceptionGroup("bar", (ValueError(),))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, match="foo"):
            raise ExceptionGroup("bar", (ValueError(),))


def test_check() -> None:
    exc = ExceptionGroup("", (ValueError(),))
    with RaisesGroup(ValueError, check=lambda x: x is exc):
        raise exc
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(ValueError, check=lambda x: x is exc):
            raise ExceptionGroup("", (ValueError(),))


def test_RaisesGroup_matches() -> None:
    rg = RaisesGroup(ValueError)
    assert not rg.matches(None)
    assert not rg.matches(ValueError())
    assert rg.matches(ExceptionGroup("", (ValueError(),)))


def test_message() -> None:
    def check_message(message: str, body: RaisesGroup[Any]) -> None:
        with pytest.raises(
            AssertionError,
            match=f"^DID NOT RAISE any exception, expected {re.escape(message)}$",
        ):
            with body:
                ...

    # basic
    check_message("ExceptionGroup(ValueError)", RaisesGroup(ValueError))
    # multiple exceptions
    check_message(
        "ExceptionGroup(ValueError, ValueError)", RaisesGroup(ValueError, ValueError)
    )
    # nested
    check_message(
        "ExceptionGroup(ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(ValueError)),
    )

    # Matcher
    check_message(
        "ExceptionGroup(Matcher(ValueError, match='my_str'))",
        RaisesGroup(Matcher(ValueError, "my_str")),
    )
    check_message(
        "ExceptionGroup(Matcher(match='my_str'))",
        RaisesGroup(Matcher(match="my_str")),
    )

    # BaseExceptionGroup
    check_message(
        "BaseExceptionGroup(KeyboardInterrupt)", RaisesGroup(KeyboardInterrupt)
    )
    # BaseExceptionGroup with type inside Matcher
    check_message(
        "BaseExceptionGroup(Matcher(KeyboardInterrupt))",
        RaisesGroup(Matcher(KeyboardInterrupt)),
    )
    # Base-ness transfers to parent containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt)),
    )
    # but not to child containers
    check_message(
        "BaseExceptionGroup(BaseExceptionGroup(KeyboardInterrupt), ExceptionGroup(ValueError))",
        RaisesGroup(RaisesGroup(KeyboardInterrupt), RaisesGroup(ValueError)),
    )


def test_matcher() -> None:
    with pytest.raises(
        ValueError, match="^You must specify at least one parameter to match on.$"
    ):
        Matcher()  # type: ignore[call-overload]
    with pytest.raises(
        ValueError,
        match=f"^exception_type {re.escape(repr(object))} must be a subclass of BaseException$",
    ):
        Matcher(object)  # type: ignore[type-var]

    with RaisesGroup(Matcher(ValueError)):
        raise ExceptionGroup("", (ValueError(),))
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(TypeError)):
            raise ExceptionGroup("", (ValueError(),))


def test_matcher_match() -> None:
    with RaisesGroup(Matcher(ValueError, "foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(ValueError, "foo")):
            raise ExceptionGroup("", (ValueError("bar"),))

    # Can be used without specifying the type
    with RaisesGroup(Matcher(match="foo")):
        raise ExceptionGroup("", (ValueError("foo"),))
    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(match="foo")):
            raise ExceptionGroup("", (ValueError("bar"),))


def test_Matcher_check() -> None:
    def check_oserror_and_errno_is_5(e: BaseException) -> bool:
        return isinstance(e, OSError) and e.errno == 5

    with RaisesGroup(Matcher(check=check_oserror_and_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    # specifying exception_type narrows the parameter type to the callable
    def check_errno_is_5(e: OSError) -> bool:
        return e.errno == 5

    with RaisesGroup(Matcher(OSError, check=check_errno_is_5)):
        raise ExceptionGroup("", (OSError(5, ""),))

    with pytest.raises(ExceptionGroup):
        with RaisesGroup(Matcher(OSError, check=check_errno_is_5)):
            raise ExceptionGroup("", (OSError(6, ""),))


def test_matcher_tostring() -> None:
    assert str(Matcher(ValueError)) == "Matcher(ValueError)"
    assert str(Matcher(match="[a-z]")) == "Matcher(match='[a-z]')"
    pattern_no_flags = re.compile("noflag", 0)
    assert str(Matcher(match=pattern_no_flags)) == "Matcher(match='noflag')"
    pattern_flags = re.compile("noflag", re.IGNORECASE)
    assert str(Matcher(match=pattern_flags)) == f"Matcher(match={pattern_flags!r})"
    assert (
        str(Matcher(ValueError, match="re", check=bool))
        == f"Matcher(ValueError, match='re', check={bool!r})"
    )


def test__ExceptionInfo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        trio.testing._raises_group,
        "ExceptionInfo",
        trio.testing._raises_group._ExceptionInfo,
    )
    with trio.testing.RaisesGroup(ValueError) as excinfo:
        raise ExceptionGroup("", (ValueError("hello"),))
    assert excinfo.type is ExceptionGroup
    assert excinfo.value.exceptions[0].args == ("hello",)
    assert isinstance(excinfo.tb, TracebackType)
