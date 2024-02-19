"""The typing of RaisesGroup involves a lot of deception and lies, since AFAIK what we
actually want to achieve is ~impossible. This is because we specify what we expect with
instances of RaisesGroup and exception classes, but excinfo.value will be instances of
[Base]ExceptionGroup and instances of exceptions. So we need to "translate" from
RaisesGroup to ExceptionGroup.

The way it currently works is that RaisesGroup[E] corresponds to
ExceptionInfo[BaseExceptionGroup[E]], so the top-level group will be correct. But
RaisesGroup[RaisesGroup[ValueError]] will become
ExceptionInfo[BaseExceptionGroup[RaisesGroup[ValueError]]]. To get around that we specify
RaisesGroup as a subclass of BaseExceptionGroup during type checking - which should mean
that most static type checking for end users should be mostly correct.
"""
from __future__ import annotations

import sys
from typing import Union

from trio.testing import Matcher, RaisesGroup
from typing_extensions import assert_type

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup

# split into functions to isolate the different scopes


def check_inheritance_and_assignments() -> None:
    # Check inheritance
    _: BaseExceptionGroup[ValueError] = RaisesGroup(ValueError)
    _ = RaisesGroup(RaisesGroup(ValueError))  # type: ignore

    a: BaseExceptionGroup[BaseExceptionGroup[ValueError]]
    a = RaisesGroup(RaisesGroup(ValueError))
    # pyright-ignore due to bug in exceptiongroup
    # https://github.com/agronholm/exceptiongroup/pull/101
    # once fixed we'll get errors for unnecessary-pyright-ignore and can clean up
    a = BaseExceptionGroup(
        "", (BaseExceptionGroup("", (ValueError(),)),)  # pyright: ignore
    )
    assert a


def check_basic_contextmanager() -> None:
    # One level of Group is correctly translated - except it's a BaseExceptionGroup
    # instead of an ExceptionGroup.
    with RaisesGroup(ValueError) as e:
        raise ExceptionGroup("foo", (ValueError(),))
    assert_type(e.value, BaseExceptionGroup[ValueError])


def check_basic_matches() -> None:
    # check that matches gets rid of the naked ValueError in the union
    exc: ExceptionGroup[ValueError] | ValueError = ExceptionGroup("", (ValueError(),))
    if RaisesGroup(ValueError).matches(exc):
        assert_type(exc, BaseExceptionGroup[ValueError])


def check_matches_with_different_exception_type() -> None:
    # This should probably raise some type error somewhere, since
    # ValueError != KeyboardInterrupt
    e: BaseExceptionGroup[KeyboardInterrupt] = BaseExceptionGroup(
        "", (KeyboardInterrupt(),)
    )
    if RaisesGroup(ValueError).matches(e):
        assert_type(e, BaseExceptionGroup[ValueError])


def check_matcher_init() -> None:
    def check_exc(exc: BaseException) -> bool:
        return isinstance(exc, ValueError)

    def check_filenotfound(exc: FileNotFoundError) -> bool:
        return not exc.filename.endswith(".tmp")

    # Check various combinations of constructor signatures.
    # At least 1 arg must be provided. If exception_type is provided, that narrows
    # check's argument.
    Matcher()  # type: ignore
    Matcher(ValueError)
    Matcher(ValueError, "regex")
    Matcher(ValueError, "regex", check_exc)
    Matcher(exception_type=ValueError)
    Matcher(match="regex")
    Matcher(check=check_exc)
    Matcher(check=check_filenotfound)  # type: ignore
    Matcher(ValueError, match="regex")
    Matcher(FileNotFoundError, check=check_filenotfound)
    Matcher(match="regex", check=check_exc)
    Matcher(FileNotFoundError, match="regex", check=check_filenotfound)


def check_matcher_transparent() -> None:
    with RaisesGroup(Matcher(ValueError)) as e:
        ...
    _: BaseExceptionGroup[ValueError] = e.value
    assert_type(e.value, BaseExceptionGroup[ValueError])


def check_nested_raisesgroups_contextmanager() -> None:
    with RaisesGroup(RaisesGroup(ValueError)) as excinfo:
        raise ExceptionGroup("foo", (ValueError(),))

    # thanks to inheritance this assignment works
    _: BaseExceptionGroup[BaseExceptionGroup[ValueError]] = excinfo.value
    # and it can mostly be treated like an exceptiongroup
    print(excinfo.value.exceptions[0].exceptions[0])

    # but assert_type reveals the lies
    print(type(excinfo.value))  # would print "ExceptionGroup"
    # typing says it's a BaseExceptionGroup
    assert_type(
        excinfo.value,
        BaseExceptionGroup[RaisesGroup[ValueError]],
    )

    print(type(excinfo.value.exceptions[0]))  # would print "ExceptionGroup"
    # but type checkers are utterly confused
    assert_type(
        excinfo.value.exceptions[0],
        Union[RaisesGroup[ValueError], BaseExceptionGroup[RaisesGroup[ValueError]]],
    )


def check_nested_raisesgroups_matches() -> None:
    """Check nested RaisesGroups with .matches"""
    # pyright-ignore due to bug in exceptiongroup
    # https://github.com/agronholm/exceptiongroup/pull/101
    # once fixed we'll get errors for unnecessary-pyright-ignore and can clean up
    exc: ExceptionGroup[ExceptionGroup[ValueError]] = ExceptionGroup(
        "", (ExceptionGroup("", (ValueError(),)),)  # pyright: ignore
    )
    # has the same problems as check_nested_raisesgroups_contextmanager
    if RaisesGroup(RaisesGroup(ValueError)).matches(exc):
        assert_type(exc, BaseExceptionGroup[RaisesGroup[ValueError]])
