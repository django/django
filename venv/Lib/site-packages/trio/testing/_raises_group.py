from __future__ import annotations

import re
import sys
from abc import ABC, abstractmethod
from re import Pattern
from textwrap import indent
from typing import TYPE_CHECKING, Generic, Literal, TypeGuard, cast, overload

from trio._util import final

if TYPE_CHECKING:
    import builtins

    # sphinx will *only* work if we use types.TracebackType, and import
    # *inside* TYPE_CHECKING. No other combination works.....
    import types
    from collections.abc import Callable, Sequence

    from _pytest._code.code import ExceptionChainRepr, ReprExceptionInfo, Traceback
    from typing_extensions import TypeVar

    # this conditional definition is because we want to allow a TypeVar default
    MatchE = TypeVar(
        "MatchE",
        bound=BaseException,
        default=BaseException,
        covariant=True,
    )
else:
    from typing import TypeVar

    MatchE = TypeVar("MatchE", bound=BaseException, covariant=True)

# RaisesGroup doesn't work with a default.
BaseExcT_co = TypeVar("BaseExcT_co", bound=BaseException, covariant=True)
BaseExcT_1 = TypeVar("BaseExcT_1", bound=BaseException)
BaseExcT_2 = TypeVar("BaseExcT_2", bound=BaseException)
ExcT_1 = TypeVar("ExcT_1", bound=Exception)
ExcT_2 = TypeVar("ExcT_2", bound=Exception)

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


@final
class _ExceptionInfo(Generic[MatchE]):
    """Minimal re-implementation of pytest.ExceptionInfo, only used if pytest is not available. Supports a subset of its features necessary for functionality of :class:`trio.testing.RaisesGroup` and :class:`trio.testing.Matcher`."""

    _excinfo: tuple[type[MatchE], MatchE, types.TracebackType] | None

    def __init__(
        self,
        excinfo: tuple[type[MatchE], MatchE, types.TracebackType] | None,
    ) -> None:
        self._excinfo = excinfo

    def fill_unfilled(
        self,
        exc_info: tuple[type[MatchE], MatchE, types.TracebackType],
    ) -> None:
        """Fill an unfilled ExceptionInfo created with ``for_later()``."""
        assert self._excinfo is None, "ExceptionInfo was already filled"
        self._excinfo = exc_info

    @classmethod
    def for_later(cls) -> _ExceptionInfo[MatchE]:
        """Return an unfilled ExceptionInfo."""
        return cls(None)

    # Note, special cased in sphinx config, since "type" conflicts.
    @property
    def type(self) -> type[MatchE]:
        """The exception class."""
        assert (
            self._excinfo is not None
        ), ".type can only be used after the context manager exits"
        return self._excinfo[0]

    @property
    def value(self) -> MatchE:
        """The exception value."""
        assert (
            self._excinfo is not None
        ), ".value can only be used after the context manager exits"
        return self._excinfo[1]

    @property
    def tb(self) -> types.TracebackType:
        """The exception raw traceback."""
        assert (
            self._excinfo is not None
        ), ".tb can only be used after the context manager exits"
        return self._excinfo[2]

    def exconly(self, tryshort: bool = False) -> str:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed",
        )

    def errisinstance(
        self,
        exc: builtins.type[BaseException] | tuple[builtins.type[BaseException], ...],
    ) -> bool:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed",
        )

    def getrepr(
        self,
        showlocals: bool = False,
        style: str = "long",
        abspath: bool = False,
        tbfilter: bool | Callable[[_ExceptionInfo], Traceback] = True,
        funcargs: bool = False,
        truncate_locals: bool = True,
        chain: bool = True,
    ) -> ReprExceptionInfo | ExceptionChainRepr:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed",
        )


# Type checkers are not able to do conditional types depending on installed packages, so
# we've added signatures for all helpers to _ExceptionInfo, and then always use that.
# If this ends up leading to problems, we can resort to always using _ExceptionInfo and
# users that want to use getrepr/errisinstance/exconly can write helpers on their own, or
# we reimplement them ourselves...or get this merged in upstream pytest.
if TYPE_CHECKING:
    ExceptionInfo = _ExceptionInfo

else:
    try:
        from pytest import ExceptionInfo  # noqa: PT013
    except ImportError:  # pragma: no cover
        ExceptionInfo = _ExceptionInfo


# copied from pytest.ExceptionInfo
def _stringify_exception(exc: BaseException) -> str:
    return "\n".join(
        [
            getattr(exc, "message", str(exc)),
            *getattr(exc, "__notes__", []),
        ],
    )


# String patterns default to including the unicode flag.
_REGEX_NO_FLAGS = re.compile(r"").flags


def _match_pattern(match: Pattern[str]) -> str | Pattern[str]:
    """helper function to remove redundant `re.compile` calls when printing regex"""
    return match.pattern if match.flags == _REGEX_NO_FLAGS else match


def repr_callable(fun: Callable[[BaseExcT_1], bool]) -> str:
    """Get the repr of a ``check`` parameter.

    Split out so it can be monkeypatched (e.g. by our hypothesis plugin)
    """
    return repr(fun)


def _exception_type_name(e: type[BaseException]) -> str:
    return repr(e.__name__)


def _check_raw_type(
    expected_type: type[BaseException] | None,
    exception: BaseException,
) -> str | None:
    if expected_type is None:
        return None

    if not isinstance(
        exception,
        expected_type,
    ):
        actual_type_str = _exception_type_name(type(exception))
        expected_type_str = _exception_type_name(expected_type)
        if isinstance(exception, BaseExceptionGroup) and not issubclass(
            expected_type, BaseExceptionGroup
        ):
            return f"Unexpected nested {actual_type_str}, expected {expected_type_str}"
        return f"{actual_type_str} is not of type {expected_type_str}"
    return None


class AbstractMatcher(ABC, Generic[BaseExcT_co]):
    """ABC with common functionality shared between Matcher and RaisesGroup"""

    def __init__(
        self,
        match: str | Pattern[str] | None,
        check: Callable[[BaseExcT_co], bool] | None,
    ) -> None:
        if isinstance(match, str):
            self.match: Pattern[str] | None = re.compile(match)
        else:
            self.match = match
        self.check = check
        self._fail_reason: str | None = None

        # used to suppress repeated printing of `repr(self.check)`
        self._nested: bool = False

    @property
    def fail_reason(self) -> str | None:
        """Set after a call to `matches` to give a human-readable
        reason for why the match failed.
        When used as a context manager the string will be given as the text of an
        `AssertionError`"""
        return self._fail_reason

    def _check_check(
        self: AbstractMatcher[BaseExcT_1],
        exception: BaseExcT_1,
    ) -> bool:
        if self.check is None:
            return True

        if self.check(exception):
            return True

        check_repr = "" if self._nested else " " + repr_callable(self.check)
        self._fail_reason = f"check{check_repr} did not return True"
        return False

    def _check_match(self, e: BaseException) -> bool:
        if self.match is None or re.search(
            self.match,
            stringified_exception := _stringify_exception(e),
        ):
            return True

        maybe_specify_type = (
            f" of {_exception_type_name(type(e))}"
            if isinstance(e, BaseExceptionGroup)
            else ""
        )
        self._fail_reason = f"Regex pattern {_match_pattern(self.match)!r} did not match {stringified_exception!r}{maybe_specify_type}"
        if _match_pattern(self.match) == stringified_exception:
            self._fail_reason += "\n  Did you mean to `re.escape()` the regex?"
        return False

    # TODO: when transitioning to pytest, harmonize Matcher and RaisesGroup
    # signatures. One names the parameter `exc_val` and the other `exception`
    @abstractmethod
    def matches(
        self: AbstractMatcher[BaseExcT_1], exc_val: BaseException
    ) -> TypeGuard[BaseExcT_1]:
        """Check if an exception matches the requirements of this AbstractMatcher.
        If it fails, `AbstractMatcher.fail_reason` should be set.
        """


@final
class Matcher(AbstractMatcher[MatchE]):
    """Helper class to be used together with RaisesGroups when you want to specify requirements on sub-exceptions. Only specifying the type is redundant, and it's also unnecessary when the type is a nested `RaisesGroup` since it supports the same arguments.
    The type is checked with `isinstance`, and does not need to be an exact match. If that is wanted you can use the ``check`` parameter.
    :meth:`Matcher.matches` can also be used standalone to check individual exceptions.

    Examples::

        with RaisesGroups(Matcher(ValueError, match="string")):
            ...
        with RaisesGroups(Matcher(check=lambda x: x.args == (3, "hello"))):
            ...
        with RaisesGroups(Matcher(check=lambda x: type(x) is ValueError)):
            ...

    Tip: if you install ``hypothesis`` and import it in ``conftest.py`` you will get
    readable ``repr``s of ``check`` callables in the output.
    """

    # At least one of the three parameters must be passed.
    @overload
    def __init__(
        self,
        exception_type: type[MatchE],
        match: str | Pattern[str] = ...,
        check: Callable[[MatchE], bool] = ...,
    ) -> None: ...

    @overload
    def __init__(
        self: Matcher[BaseException],  # Give E a value.
        *,
        match: str | Pattern[str],
        # If exception_type is not provided, check() must do any typechecks itself.
        check: Callable[[BaseException], bool] = ...,
    ) -> None: ...

    @overload
    def __init__(self, *, check: Callable[[BaseException], bool]) -> None: ...

    def __init__(
        self,
        exception_type: type[MatchE] | None = None,
        match: str | Pattern[str] | None = None,
        check: Callable[[MatchE], bool] | None = None,
    ):
        super().__init__(match, check)
        if exception_type is None and match is None and check is None:
            raise ValueError("You must specify at least one parameter to match on.")
        if exception_type is not None and not issubclass(exception_type, BaseException):
            raise ValueError(
                f"exception_type {exception_type} must be a subclass of BaseException",
            )
        self.exception_type = exception_type

    def matches(
        self,
        exception: BaseException,
    ) -> TypeGuard[MatchE]:
        """Check if an exception matches the requirements of this Matcher.
        If it fails, `Matcher.fail_reason` will be set.

        Examples::

            assert Matcher(ValueError).matches(my_exception)
            # is equivalent to
            assert isinstance(my_exception, ValueError)

            # this can be useful when checking e.g. the ``__cause__`` of an exception.
            with pytest.raises(ValueError) as excinfo:
                ...
            assert Matcher(SyntaxError, match="foo").matches(excinfo.value.__cause__)
            # above line is equivalent to
            assert isinstance(excinfo.value.__cause__, SyntaxError)
            assert re.search("foo", str(excinfo.value.__cause__))

        """
        if not self._check_type(exception):
            return False

        if not self._check_match(exception):
            return False

        return self._check_check(exception)

    def __repr__(self) -> str:
        parameters = []
        if self.exception_type is not None:
            parameters.append(self.exception_type.__name__)
        if self.match is not None:
            # If no flags were specified, discard the redundant re.compile() here.
            parameters.append(
                f"match={_match_pattern(self.match)!r}",
            )
        if self.check is not None:
            parameters.append(f"check={repr_callable(self.check)}")
        return f'Matcher({", ".join(parameters)})'

    def _check_type(self, exception: BaseException) -> TypeGuard[MatchE]:
        self._fail_reason = _check_raw_type(self.exception_type, exception)
        return self._fail_reason is None


@final
class RaisesGroup(AbstractMatcher[BaseExceptionGroup[BaseExcT_co]]):
    """Contextmanager for checking for an expected `ExceptionGroup`.
    This works similar to ``pytest.raises``, and a version of it will hopefully be added upstream, after which this can be deprecated and removed. See https://github.com/pytest-dev/pytest/issues/11538


    The catching behaviour differs from :ref:`except* <except_star>` in multiple different ways, being much stricter by default. By using ``allow_unwrapped=True`` and ``flatten_subgroups=True`` you can match ``except*`` fully when expecting a single exception.

    #. All specified exceptions must be present, *and no others*.

       * If you expect a variable number of exceptions you need to use ``pytest.raises(ExceptionGroup)`` and manually check the contained exceptions. Consider making use of :func:`Matcher.matches`.

    #. It will only catch exceptions wrapped in an exceptiongroup by default.

       * With ``allow_unwrapped=True`` you can specify a single expected exception or `Matcher` and it will match the exception even if it is not inside an `ExceptionGroup`. If you expect one of several different exception types you need to use a `Matcher` object.

    #. By default it cares about the full structure with nested `ExceptionGroup`'s. You can specify nested `ExceptionGroup`'s by passing `RaisesGroup` objects as expected exceptions.

       * With ``flatten_subgroups=True`` it will "flatten" the raised `ExceptionGroup`, extracting all exceptions inside any nested :class:`ExceptionGroup`, before matching.

    It does not care about the order of the exceptions, so ``RaisesGroups(ValueError, TypeError)`` is equivalent to ``RaisesGroups(TypeError, ValueError)``.

    Examples::

        with RaisesGroups(ValueError):
            raise ExceptionGroup("", (ValueError(),))
        with RaisesGroups(ValueError, ValueError, Matcher(TypeError, match="expected int")):
            ...
        with RaisesGroups(KeyboardInterrupt, match="hello", check=lambda x: type(x) is BaseExceptionGroup):
            ...
        with RaisesGroups(RaisesGroups(ValueError)):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

        # flatten_subgroups
        with RaisesGroups(ValueError, flatten_subgroups=True):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

        # allow_unwrapped
        with RaisesGroups(ValueError, allow_unwrapped=True):
            raise ValueError


    `RaisesGroup.matches` can also be used directly to check a standalone exception group.


    The matching algorithm is greedy, which means cases such as this may fail::

        with RaisesGroups(ValueError, Matcher(ValueError, match="hello")):
            raise ExceptionGroup("", (ValueError("hello"), ValueError("goodbye")))

    even though it generally does not care about the order of the exceptions in the group.
    To avoid the above you should specify the first ValueError with a Matcher as well.

    Tip: if you install ``hypothesis`` and import it in ``conftest.py`` you will get
    readable ``repr``s of ``check`` callables in the output.
    """

    # allow_unwrapped=True requires: singular exception, exception not being
    # RaisesGroup instance, match is None, check is None
    @overload
    def __init__(
        self,
        exception: type[BaseExcT_co] | Matcher[BaseExcT_co],
        *,
        allow_unwrapped: Literal[True],
        flatten_subgroups: bool = False,
    ) -> None: ...

    # flatten_subgroups = True also requires no nested RaisesGroup
    @overload
    def __init__(
        self,
        exception: type[BaseExcT_co] | Matcher[BaseExcT_co],
        *other_exceptions: type[BaseExcT_co] | Matcher[BaseExcT_co],
        flatten_subgroups: Literal[True],
        match: str | Pattern[str] | None = None,
        check: Callable[[BaseExceptionGroup[BaseExcT_co]], bool] | None = None,
    ) -> None: ...

    # simplify the typevars if possible (the following 3 are equivalent but go simpler->complicated)
    # ... the first handles RaisesGroup[ValueError], the second RaisesGroup[ExceptionGroup[ValueError]],
    #     the third RaisesGroup[ValueError | ExceptionGroup[ValueError]].
    # ... otherwise, we will get results like RaisesGroup[ValueError | ExceptionGroup[Never]] (I think)
    #     (technically correct but misleading)
    @overload
    def __init__(
        self: RaisesGroup[ExcT_1],
        exception: type[ExcT_1] | Matcher[ExcT_1],
        *other_exceptions: type[ExcT_1] | Matcher[ExcT_1],
        match: str | Pattern[str] | None = None,
        check: Callable[[ExceptionGroup[ExcT_1]], bool] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[ExceptionGroup[ExcT_2]],
        exception: RaisesGroup[ExcT_2],
        *other_exceptions: RaisesGroup[ExcT_2],
        match: str | Pattern[str] | None = None,
        check: Callable[[ExceptionGroup[ExceptionGroup[ExcT_2]]], bool] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[ExcT_1 | ExceptionGroup[ExcT_2]],
        exception: type[ExcT_1] | Matcher[ExcT_1] | RaisesGroup[ExcT_2],
        *other_exceptions: type[ExcT_1] | Matcher[ExcT_1] | RaisesGroup[ExcT_2],
        match: str | Pattern[str] | None = None,
        check: (
            Callable[[ExceptionGroup[ExcT_1 | ExceptionGroup[ExcT_2]]], bool] | None
        ) = None,
    ) -> None: ...

    # same as the above 3 but handling BaseException
    @overload
    def __init__(
        self: RaisesGroup[BaseExcT_1],
        exception: type[BaseExcT_1] | Matcher[BaseExcT_1],
        *other_exceptions: type[BaseExcT_1] | Matcher[BaseExcT_1],
        match: str | Pattern[str] | None = None,
        check: Callable[[BaseExceptionGroup[BaseExcT_1]], bool] | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[BaseExceptionGroup[BaseExcT_2]],
        exception: RaisesGroup[BaseExcT_2],
        *other_exceptions: RaisesGroup[BaseExcT_2],
        match: str | Pattern[str] | None = None,
        check: (
            Callable[[BaseExceptionGroup[BaseExceptionGroup[BaseExcT_2]]], bool] | None
        ) = None,
    ) -> None: ...

    @overload
    def __init__(
        self: RaisesGroup[BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]],
        exception: type[BaseExcT_1] | Matcher[BaseExcT_1] | RaisesGroup[BaseExcT_2],
        *other_exceptions: type[BaseExcT_1]
        | Matcher[BaseExcT_1]
        | RaisesGroup[BaseExcT_2],
        match: str | Pattern[str] | None = None,
        check: (
            Callable[
                [BaseExceptionGroup[BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]]],
                bool,
            ]
            | None
        ) = None,
    ) -> None: ...

    def __init__(
        self: RaisesGroup[ExcT_1 | BaseExcT_1 | BaseExceptionGroup[BaseExcT_2]],
        exception: type[BaseExcT_1] | Matcher[BaseExcT_1] | RaisesGroup[BaseExcT_2],
        *other_exceptions: type[BaseExcT_1]
        | Matcher[BaseExcT_1]
        | RaisesGroup[BaseExcT_2],
        allow_unwrapped: bool = False,
        flatten_subgroups: bool = False,
        match: str | Pattern[str] | None = None,
        check: (
            Callable[[BaseExceptionGroup[BaseExcT_1]], bool]
            | Callable[[ExceptionGroup[ExcT_1]], bool]
            | None
        ) = None,
    ):
        # The type hint on the `self` and `check` parameters uses different formats
        # that are *very* hard to reconcile while adhering to the overloads, so we cast
        # it to avoid an error when passing it to super().__init__
        check = cast(
            "Callable[["
            "BaseExceptionGroup[ExcT_1|BaseExcT_1|BaseExceptionGroup[BaseExcT_2]]"
            "], bool]",
            check,
        )
        super().__init__(match, check)
        self.expected_exceptions: tuple[
            type[BaseExcT_co] | Matcher[BaseExcT_co] | RaisesGroup[BaseException], ...
        ] = (
            exception,
            *other_exceptions,
        )
        self.allow_unwrapped = allow_unwrapped
        self.flatten_subgroups: bool = flatten_subgroups
        self.is_baseexceptiongroup: bool = False

        if allow_unwrapped and other_exceptions:
            raise ValueError(
                "You cannot specify multiple exceptions with `allow_unwrapped=True.`"
                " If you want to match one of multiple possible exceptions you should"
                " use a `Matcher`."
                " E.g. `Matcher(check=lambda e: isinstance(e, (...)))`",
            )
        if allow_unwrapped and isinstance(exception, RaisesGroup):
            raise ValueError(
                "`allow_unwrapped=True` has no effect when expecting a `RaisesGroup`."
                " You might want it in the expected `RaisesGroup`, or"
                " `flatten_subgroups=True` if you don't care about the structure.",
            )
        if allow_unwrapped and (match is not None or check is not None):
            raise ValueError(
                "`allow_unwrapped=True` bypasses the `match` and `check` parameters"
                " if the exception is unwrapped. If you intended to match/check the"
                " exception you should use a `Matcher` object. If you want to match/check"
                " the exceptiongroup when the exception *is* wrapped you need to"
                " do e.g. `if isinstance(exc.value, ExceptionGroup):"
                " assert RaisesGroup(...).matches(exc.value)` afterwards.",
            )

        # verify `expected_exceptions` and set `self.is_baseexceptiongroup`
        for exc in self.expected_exceptions:
            if isinstance(exc, RaisesGroup):
                if self.flatten_subgroups:
                    raise ValueError(
                        "You cannot specify a nested structure inside a RaisesGroup with"
                        " `flatten_subgroups=True`. The parameter will flatten subgroups"
                        " in the raised exceptiongroup before matching, which would never"
                        " match a nested structure.",
                    )
                self.is_baseexceptiongroup |= exc.is_baseexceptiongroup
                exc._nested = True
            elif isinstance(exc, Matcher):
                if exc.exception_type is not None:
                    # Matcher __init__ assures it's a subclass of BaseException
                    self.is_baseexceptiongroup |= not issubclass(
                        exc.exception_type,
                        Exception,
                    )
                exc._nested = True
            elif isinstance(exc, type) and issubclass(exc, BaseException):
                self.is_baseexceptiongroup |= not issubclass(exc, Exception)
            else:
                raise ValueError(
                    f'Invalid argument "{exc!r}" must be exception type, Matcher, or'
                    " RaisesGroup.",
                )

    @overload
    def __enter__(
        self: RaisesGroup[ExcT_1],
    ) -> ExceptionInfo[ExceptionGroup[ExcT_1]]: ...
    @overload
    def __enter__(
        self: RaisesGroup[BaseExcT_1],
    ) -> ExceptionInfo[BaseExceptionGroup[BaseExcT_1]]: ...

    def __enter__(self) -> ExceptionInfo[BaseExceptionGroup[BaseException]]:
        self.excinfo: ExceptionInfo[BaseExceptionGroup[BaseExcT_co]] = (
            ExceptionInfo.for_later()
        )
        return self.excinfo

    def __repr__(self) -> str:
        parameters = [
            e.__name__ if isinstance(e, type) else repr(e)
            for e in self.expected_exceptions
        ]
        if self.allow_unwrapped:
            parameters.append(f"allow_unwrapped={self.allow_unwrapped}")
        if self.flatten_subgroups:
            parameters.append(f"flatten_subgroups={self.flatten_subgroups}")
        if self.match is not None:
            # If no flags were specified, discard the redundant re.compile() here.
            parameters.append(f"match={_match_pattern(self.match)!r}")
        if self.check is not None:
            parameters.append(f"check={repr_callable(self.check)}")
        return f"RaisesGroup({', '.join(parameters)})"

    def _unroll_exceptions(
        self,
        exceptions: Sequence[BaseException],
    ) -> Sequence[BaseException]:
        """Used if `flatten_subgroups=True`."""
        res: list[BaseException] = []
        for exc in exceptions:
            if isinstance(exc, BaseExceptionGroup):
                res.extend(self._unroll_exceptions(exc.exceptions))

            else:
                res.append(exc)
        return res

    @overload
    def matches(
        self: RaisesGroup[ExcT_1],
        exc_val: BaseException | None,
    ) -> TypeGuard[ExceptionGroup[ExcT_1]]: ...
    @overload
    def matches(
        self: RaisesGroup[BaseExcT_1],
        exc_val: BaseException | None,
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_1]]: ...

    def matches(
        self,
        exc_val: BaseException | None,
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_co]]:
        """Check if an exception matches the requirements of this RaisesGroup.
        If it fails, `RaisesGroup.fail_reason` will be set.

        Example::

            with pytest.raises(TypeError) as excinfo:
                ...
            assert RaisesGroups(ValueError).matches(excinfo.value.__cause__)
            # the above line is equivalent to
            myexc = excinfo.value.__cause
            assert isinstance(myexc, BaseExceptionGroup)
            assert len(myexc.exceptions) == 1
            assert isinstance(myexc.exceptions[0], ValueError)
        """
        self._fail_reason = None
        if exc_val is None:
            self._fail_reason = "exception is None"
            return False
        if not isinstance(exc_val, BaseExceptionGroup):
            # we opt to only print type of the exception here, as the repr would
            # likely be quite long
            not_group_msg = f"{type(exc_val).__name__!r} is not an exception group"
            if len(self.expected_exceptions) > 1:
                self._fail_reason = not_group_msg
                return False
            # if we have 1 expected exception, check if it would work even if
            # allow_unwrapped is not set
            res = self._check_expected(self.expected_exceptions[0], exc_val)
            if res is None and self.allow_unwrapped:
                return True

            if res is None:
                self._fail_reason = (
                    f"{not_group_msg}, but would match with `allow_unwrapped=True`"
                )
            elif self.allow_unwrapped:
                self._fail_reason = res
            else:
                self._fail_reason = not_group_msg
            return False

        actual_exceptions: Sequence[BaseException] = exc_val.exceptions
        if self.flatten_subgroups:
            actual_exceptions = self._unroll_exceptions(actual_exceptions)

        if not self._check_match(exc_val):
            old_reason = self._fail_reason
            if (
                len(actual_exceptions) == len(self.expected_exceptions) == 1
                and isinstance(expected := self.expected_exceptions[0], type)
                and isinstance(actual := actual_exceptions[0], expected)
                and self._check_match(actual)
            ):
                assert self.match is not None, "can't be None if _check_match failed"
                assert self._fail_reason is old_reason is not None
                self._fail_reason += f", but matched the expected {self._repr_expected(expected)}. You might want RaisesGroup(Matcher({expected.__name__}, match={_match_pattern(self.match)!r}))"
            else:
                self._fail_reason = old_reason
            return False

        # do the full check on expected exceptions
        if not self._check_exceptions(
            exc_val,
            actual_exceptions,
        ):
            assert self._fail_reason is not None
            old_reason = self._fail_reason
            # if we're not expecting a nested structure, and there is one, do a second
            # pass where we try flattening it
            if (
                not self.flatten_subgroups
                and not any(
                    isinstance(e, RaisesGroup) for e in self.expected_exceptions
                )
                and any(isinstance(e, BaseExceptionGroup) for e in actual_exceptions)
                and self._check_exceptions(
                    exc_val,
                    self._unroll_exceptions(exc_val.exceptions),
                )
            ):
                # only indent if it's a single-line reason. In a multi-line there's already
                # indented lines that this does not belong to.
                indent = "  " if "\n" not in self._fail_reason else ""
                self._fail_reason = (
                    old_reason
                    + f"\n{indent}Did you mean to use `flatten_subgroups=True`?"
                )
            else:
                self._fail_reason = old_reason
            return False

        # Only run `self.check` once we know `exc_val` is of the correct type.
        # TODO: if this fails, we should say the *group* did not match
        return self._check_check(exc_val)

    @staticmethod
    def _check_expected(
        expected_type: (
            type[BaseException] | Matcher[BaseException] | RaisesGroup[BaseException]
        ),
        exception: BaseException,
    ) -> str | None:
        """Helper method for `RaisesGroup.matches` and `RaisesGroup._check_exceptions`
        to check one of potentially several expected exceptions."""
        if isinstance(expected_type, type):
            return _check_raw_type(expected_type, exception)
        res = expected_type.matches(exception)
        if res:
            return None
        assert expected_type.fail_reason is not None
        if expected_type.fail_reason.startswith("\n"):
            return f"\n{expected_type!r}: {indent(expected_type.fail_reason, '  ')}"
        return f"{expected_type!r}: {expected_type.fail_reason}"

    @staticmethod
    def _repr_expected(e: type[BaseException] | AbstractMatcher[BaseException]) -> str:
        """Get the repr of an expected type/Matcher/RaisesGroup, but we only want
        the name if it's a type"""
        if isinstance(e, type):
            return _exception_type_name(e)
        return repr(e)

    @overload
    def _check_exceptions(
        self: RaisesGroup[ExcT_1],
        _exc_val: Exception,
        actual_exceptions: Sequence[Exception],
    ) -> TypeGuard[ExceptionGroup[ExcT_1]]: ...
    @overload
    def _check_exceptions(
        self: RaisesGroup[BaseExcT_1],
        _exc_val: BaseException,
        actual_exceptions: Sequence[BaseException],
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_1]]: ...

    def _check_exceptions(
        self,
        _exc_val: BaseException,
        actual_exceptions: Sequence[BaseException],
    ) -> TypeGuard[BaseExceptionGroup[BaseExcT_co]]:
        """helper method for RaisesGroup.matches that attempts to pair up expected and actual exceptions"""
        # full table with all results
        results = ResultHolder(self.expected_exceptions, actual_exceptions)

        # (indexes of) raised exceptions that haven't (yet) found an expected
        remaining_actual = list(range(len(actual_exceptions)))
        # (indexes of) expected exceptions that haven't found a matching raised
        failed_expected: list[int] = []
        # successful greedy matches
        matches: dict[int, int] = {}

        # loop over expected exceptions first to get a more predictable result
        for i_exp, expected in enumerate(self.expected_exceptions):
            for i_rem in remaining_actual:
                res = self._check_expected(expected, actual_exceptions[i_rem])
                results.set_result(i_exp, i_rem, res)
                if res is None:
                    remaining_actual.remove(i_rem)
                    matches[i_exp] = i_rem
                    break
            else:
                failed_expected.append(i_exp)

        # All exceptions matched up successfully
        if not remaining_actual and not failed_expected:
            return True

        # in case of a single expected and single raised we simplify the output
        if 1 == len(actual_exceptions) == len(self.expected_exceptions):
            assert not matches
            self._fail_reason = res
            return False

        # The test case is failing, so we can do a slow and exhaustive check to find
        # duplicate matches etc that will be helpful in debugging
        for i_exp, expected in enumerate(self.expected_exceptions):
            for i_actual, actual in enumerate(actual_exceptions):
                if results.has_result(i_exp, i_actual):
                    continue
                results.set_result(
                    i_exp, i_actual, self._check_expected(expected, actual)
                )

        successful_str = (
            f"{len(matches)} matched exception{'s' if len(matches) > 1 else ''}. "
            if matches
            else ""
        )

        # all expected were found
        if not failed_expected and results.no_match_for_actual(remaining_actual):
            self._fail_reason = f"{successful_str}Unexpected exception(s): {[actual_exceptions[i] for i in remaining_actual]!r}"
            return False
        # all raised exceptions were expected
        if not remaining_actual and results.no_match_for_expected(failed_expected):
            self._fail_reason = f"{successful_str}Too few exceptions raised, found no match for: [{', '.join(self._repr_expected(self.expected_exceptions[i]) for i in failed_expected)}]"
            return False

        # if there's only one remaining and one failed, and the unmatched didn't match anything else,
        # we elect to only print why the remaining and the failed didn't match.
        if (
            1 == len(remaining_actual) == len(failed_expected)
            and results.no_match_for_actual(remaining_actual)
            and results.no_match_for_expected(failed_expected)
        ):
            self._fail_reason = f"{successful_str}{results.get_result(failed_expected[0], remaining_actual[0])}"
            return False

        # there's both expected and raised exceptions without matches
        s = ""
        if matches:
            s += f"\n{successful_str}"
        indent_1 = " " * 2
        indent_2 = " " * 4

        if not remaining_actual:
            s += "\nToo few exceptions raised!"
        elif not failed_expected:
            s += "\nUnexpected exception(s)!"

        if failed_expected:
            s += "\nThe following expected exceptions did not find a match:"
            rev_matches = {v: k for k, v in matches.items()}
        for i_failed in failed_expected:
            s += (
                f"\n{indent_1}{self._repr_expected(self.expected_exceptions[i_failed])}"
            )
            for i_actual, actual in enumerate(actual_exceptions):
                if results.get_result(i_exp, i_actual) is None:
                    # we print full repr of match target
                    s += f"\n{indent_2}It matches {actual!r} which was paired with {self._repr_expected(self.expected_exceptions[rev_matches[i_actual]])}"

        if remaining_actual:
            s += "\nThe following raised exceptions did not find a match"
        for i_actual in remaining_actual:
            s += f"\n{indent_1}{actual_exceptions[i_actual]!r}:"
            for i_exp, expected in enumerate(self.expected_exceptions):
                res = results.get_result(i_exp, i_actual)
                if i_exp in failed_expected:
                    assert res is not None
                    if res[0] != "\n":
                        s += "\n"
                    s += indent(res, indent_2)
                if res is None:
                    # we print full repr of match target
                    s += f"\n{indent_2}It matches {self._repr_expected(expected)} which was paired with {actual_exceptions[matches[i_exp]]!r}"

        if len(self.expected_exceptions) == len(actual_exceptions) and possible_match(
            results
        ):
            s += "\nThere exist a possible match when attempting an exhaustive check, but RaisesGroup uses a greedy algorithm. Please make your expected exceptions more stringent with `Matcher` etc so the greedy algorithm can function."
        self._fail_reason = s
        return False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        __tracebackhide__ = True
        assert (
            exc_type is not None
        ), f"DID NOT RAISE any exception, expected {self.expected_type()}"
        assert (
            self.excinfo is not None
        ), "Internal error - should have been constructed in __enter__"

        group_str = (
            "(group)"
            if self.allow_unwrapped and not issubclass(exc_type, BaseExceptionGroup)
            else "group"
        )

        assert self.matches(
            exc_val,
        ), f"Raised exception {group_str} did not match: {self._fail_reason}"

        # Cast to narrow the exception type now that it's verified.
        exc_info = cast(
            "tuple[type[BaseExceptionGroup[BaseExcT_co]], BaseExceptionGroup[BaseExcT_co], types.TracebackType]",
            (exc_type, exc_val, exc_tb),
        )
        self.excinfo.fill_unfilled(exc_info)
        return True

    def expected_type(self) -> str:
        subexcs = []
        for e in self.expected_exceptions:
            if isinstance(e, Matcher):
                subexcs.append(str(e))
            elif isinstance(e, RaisesGroup):
                subexcs.append(e.expected_type())
            elif isinstance(e, type):
                subexcs.append(e.__name__)
            else:  # pragma: no cover
                raise AssertionError("unknown type")
        group_type = "Base" if self.is_baseexceptiongroup else ""
        return f"{group_type}ExceptionGroup({', '.join(subexcs)})"


@final
class NotChecked: ...


class ResultHolder:
    def __init__(
        self,
        expected_exceptions: tuple[
            type[BaseException] | AbstractMatcher[BaseException], ...
        ],
        actual_exceptions: Sequence[BaseException],
    ) -> None:
        self.results: list[list[str | type[NotChecked] | None]] = [
            [NotChecked for _ in expected_exceptions] for _ in actual_exceptions
        ]

    def set_result(self, expected: int, actual: int, result: str | None) -> None:
        self.results[actual][expected] = result

    def get_result(self, expected: int, actual: int) -> str | None:
        res = self.results[actual][expected]
        # mypy doesn't support `assert res is not NotChecked`
        assert not isinstance(res, type)
        return res

    def has_result(self, expected: int, actual: int) -> bool:
        return self.results[actual][expected] is not NotChecked

    def no_match_for_expected(self, expected: list[int]) -> bool:
        for i in expected:
            for actual_results in self.results:
                assert actual_results[i] is not NotChecked
                if actual_results[i] is None:
                    return False
        return True

    def no_match_for_actual(self, actual: list[int]) -> bool:
        for i in actual:
            for res in self.results[i]:
                assert res is not NotChecked
                if res is None:
                    return False
        return True


def possible_match(results: ResultHolder, used: set[int] | None = None) -> bool:
    if used is None:
        used = set()
    curr_row = len(used)
    if curr_row == len(results.results):
        return True

    for i, val in enumerate(results.results[curr_row]):
        if val is None and i not in used and possible_match(results, used | {i}):
            return True
    return False
