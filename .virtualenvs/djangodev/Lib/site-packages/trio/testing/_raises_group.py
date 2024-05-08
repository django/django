from __future__ import annotations

import re
import sys
from typing import (
    TYPE_CHECKING,
    Callable,
    ContextManager,
    Generic,
    Iterable,
    Pattern,
    TypeVar,
    cast,
    overload,
)

from trio._util import final

if TYPE_CHECKING:
    import builtins

    # sphinx will *only* work if we use types.TracebackType, and import
    # *inside* TYPE_CHECKING. No other combination works.....
    import types

    from _pytest._code.code import ExceptionChainRepr, ReprExceptionInfo, Traceback
    from typing_extensions import TypeGuard

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

E = TypeVar("E", bound=BaseException)


@final
class _ExceptionInfo(Generic[E]):
    """Minimal re-implementation of pytest.ExceptionInfo, only used if pytest is not available. Supports a subset of its features necessary for functionality of :class:`trio.testing.RaisesGroup` and :class:`trio.testing.Matcher`."""

    _excinfo: tuple[type[E], E, types.TracebackType] | None

    def __init__(self, excinfo: tuple[type[E], E, types.TracebackType] | None):
        self._excinfo = excinfo

    def fill_unfilled(self, exc_info: tuple[type[E], E, types.TracebackType]) -> None:
        """Fill an unfilled ExceptionInfo created with ``for_later()``."""
        assert self._excinfo is None, "ExceptionInfo was already filled"
        self._excinfo = exc_info

    @classmethod
    def for_later(cls) -> _ExceptionInfo[E]:
        """Return an unfilled ExceptionInfo."""
        return cls(None)

    @property
    def type(self) -> type[E]:
        """The exception class."""
        assert (
            self._excinfo is not None
        ), ".type can only be used after the context manager exits"
        return self._excinfo[0]

    @property
    def value(self) -> E:
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
            "This is a helper method only available if you use RaisesGroup with the pytest package installed"
        )

    def errisinstance(
        self,
        exc: builtins.type[BaseException] | tuple[builtins.type[BaseException], ...],
    ) -> bool:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed"
        )

    def getrepr(
        self,
        showlocals: bool = False,
        style: str = "long",
        abspath: bool = False,
        tbfilter: bool | Callable[[_ExceptionInfo[BaseException]], Traceback] = True,
        funcargs: bool = False,
        truncate_locals: bool = True,
        chain: bool = True,
    ) -> ReprExceptionInfo | ExceptionChainRepr:
        raise NotImplementedError(
            "This is a helper method only available if you use RaisesGroup with the pytest package installed"
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
            str(exc),
            *getattr(exc, "__notes__", []),
        ]
    )


# String patterns default to including the unicode flag.
_regex_no_flags = re.compile("").flags


@final
class Matcher(Generic[E]):
    """Helper class to be used together with RaisesGroups when you want to specify requirements on sub-exceptions. Only specifying the type is redundant, and it's also unnecessary when the type is a nested `RaisesGroup` since it supports the same arguments.
    The type is checked with `isinstance`, and does not need to be an exact match. If that is wanted you can use the ``check`` parameter.
    :meth:`trio.testing.Matcher.matches` can also be used standalone to check individual exceptions.

    Examples::

        with RaisesGroups(Matcher(ValueError, match="string"))
            ...
        with RaisesGroups(Matcher(check=lambda x: x.args == (3, "hello"))):
            ...
        with RaisesGroups(Matcher(check=lambda x: type(x) is ValueError)):
            ...

    """

    # At least one of the three parameters must be passed.
    @overload
    def __init__(
        self: Matcher[E],
        exception_type: type[E],
        match: str | Pattern[str] = ...,
        check: Callable[[E], bool] = ...,
    ): ...

    @overload
    def __init__(
        self: Matcher[BaseException],  # Give E a value.
        *,
        match: str | Pattern[str],
        # If exception_type is not provided, check() must do any typechecks itself.
        check: Callable[[BaseException], bool] = ...,
    ): ...

    @overload
    def __init__(self, *, check: Callable[[BaseException], bool]): ...

    def __init__(
        self,
        exception_type: type[E] | None = None,
        match: str | Pattern[str] | None = None,
        check: Callable[[E], bool] | None = None,
    ):
        if exception_type is None and match is None and check is None:
            raise ValueError("You must specify at least one parameter to match on.")
        if exception_type is not None and not issubclass(exception_type, BaseException):
            raise ValueError(
                f"exception_type {exception_type} must be a subclass of BaseException"
            )
        self.exception_type = exception_type
        self.match: Pattern[str] | None
        if isinstance(match, str):
            self.match = re.compile(match)
        else:
            self.match = match
        self.check = check

    def matches(self, exception: BaseException) -> TypeGuard[E]:
        """Check if an exception matches the requirements of this Matcher.

        Examples::

            assert Matcher(ValueError).matches(my_exception):
            # is equivalent to
            assert isinstance(my_exception, ValueError)

            # this can be useful when checking e.g. the ``__cause__`` of an exception.
            with pytest.raises(ValueError) as excinfo:
                ...
            assert Matcher(SyntaxError, match="foo").matches(excinfo.value.__cause__)
            # above line is equivalent to
            assert isinstance(excinfo.value.__cause__, SyntaxError)
            assert re.search("foo", str(excinfo.value.__cause__)

        """
        if self.exception_type is not None and not isinstance(
            exception, self.exception_type
        ):
            return False
        if self.match is not None and not re.search(
            self.match, _stringify_exception(exception)
        ):
            return False
        # If exception_type is None check() accepts BaseException.
        # If non-none, we have done an isinstance check above.
        if self.check is not None and not self.check(cast(E, exception)):
            return False
        return True

    def __str__(self) -> str:
        reqs = []
        if self.exception_type is not None:
            reqs.append(self.exception_type.__name__)
        if (match := self.match) is not None:
            # If no flags were specified, discard the redundant re.compile() here.
            reqs.append(
                f"match={match.pattern if match.flags == _regex_no_flags else match!r}"
            )
        if self.check is not None:
            reqs.append(f"check={self.check!r}")
        return f'Matcher({", ".join(reqs)})'


# typing this has been somewhat of a nightmare, with the primary difficulty making
# the return type of __enter__ correct. Ideally it would function like this
# with RaisesGroup(RaisesGroup(ValueError)) as excinfo:
#   ...
# assert_type(excinfo.value, ExceptionGroup[ExceptionGroup[ValueError]])
# in addition to all the simple cases, but getting all the way to the above seems maybe
# impossible. The type being RaisesGroup[RaisesGroup[ValueError]] is probably also fine,
# as long as I add fake properties corresponding to the properties of exceptiongroup. But
# I had trouble with it handling recursive cases properly.

# Current solution settles on the above giving BaseExceptionGroup[RaisesGroup[ValueError]], and it not
# being a type error to do `with RaisesGroup(ValueError()): ...` - but that will error on runtime.

# We lie to type checkers that we inherit, so excinfo.value and sub-exceptiongroups can be treated as ExceptionGroups
if TYPE_CHECKING:
    SuperClass = BaseExceptionGroup
# Inheriting at runtime leads to a series of TypeErrors, so we do not want to do that.
else:
    SuperClass = Generic


@final
class RaisesGroup(ContextManager[ExceptionInfo[BaseExceptionGroup[E]]], SuperClass[E]):
    """Contextmanager for checking for an expected `ExceptionGroup`.
    This works similar to ``pytest.raises``, and a version of it will hopefully be added upstream, after which this can be deprecated and removed. See https://github.com/pytest-dev/pytest/issues/11538


    This differs from :ref:`except* <except_star>` in that all specified exceptions must be present, *and no others*. It will similarly not catch exceptions *not* wrapped in an exceptiongroup.
    If you don't care for the nesting level of the exceptions you can pass ``strict=False``.
    It currently does not care about the order of the exceptions, so ``RaisesGroups(ValueError, TypeError)`` is equivalent to ``RaisesGroups(TypeError, ValueError)``.

    This class is not as polished as ``pytest.raises``, and is currently not as helpful in e.g. printing diffs when strings don't match, suggesting you use ``re.escape``, etc.

    Examples::

        with RaisesGroups(ValueError):
            raise ExceptionGroup("", (ValueError(),))
        with RaisesGroups(ValueError, ValueError, Matcher(TypeError, match="expected int")):
            ...
        with RaisesGroups(KeyboardInterrupt, match="hello", check=lambda x: type(x) is BaseExceptionGroup):
            ...
        with RaisesGroups(RaisesGroups(ValueError)):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))

        with RaisesGroups(ValueError, strict=False):
            raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))


    `RaisesGroup.matches` can also be used directly to check a standalone exception group.


    This class is also not perfectly smart, e.g. this will likely fail currently::

        with RaisesGroups(ValueError, Matcher(ValueError, match="hello")):
            raise ExceptionGroup("", (ValueError("hello"), ValueError("goodbye")))

    even though it generally does not care about the order of the exceptions in the group.
    To avoid the above you should specify the first ValueError with a Matcher as well.

    It is also not typechecked perfectly, and that's likely not possible with the current approach. Most common usage should work without issue though.
    """

    # needed for pyright, since BaseExceptionGroup.__new__ takes two arguments
    if TYPE_CHECKING:

        def __new__(cls, *args: object, **kwargs: object) -> RaisesGroup[E]: ...

    def __init__(
        self,
        exception: type[E] | Matcher[E] | E,
        *other_exceptions: type[E] | Matcher[E] | E,
        strict: bool = True,
        match: str | Pattern[str] | None = None,
        check: Callable[[BaseExceptionGroup[E]], bool] | None = None,
    ):
        self.expected_exceptions: tuple[type[E] | Matcher[E] | E, ...] = (
            exception,
            *other_exceptions,
        )
        self.strict = strict
        self.match_expr = match
        self.check = check
        self.is_baseexceptiongroup = False

        for exc in self.expected_exceptions:
            if isinstance(exc, RaisesGroup):
                if not strict:
                    raise ValueError(
                        "You cannot specify a nested structure inside a RaisesGroup with"
                        " strict=False"
                    )
                self.is_baseexceptiongroup |= exc.is_baseexceptiongroup
            elif isinstance(exc, Matcher):
                if exc.exception_type is None:
                    continue
                # Matcher __init__ assures it's a subclass of BaseException
                self.is_baseexceptiongroup |= not issubclass(
                    exc.exception_type, Exception
                )
            elif isinstance(exc, type) and issubclass(exc, BaseException):
                self.is_baseexceptiongroup |= not issubclass(exc, Exception)
            else:
                raise ValueError(
                    f'Invalid argument "{exc!r}" must be exception type, Matcher, or'
                    " RaisesGroup."
                )

    def __enter__(self) -> ExceptionInfo[BaseExceptionGroup[E]]:
        self.excinfo: ExceptionInfo[BaseExceptionGroup[E]] = ExceptionInfo.for_later()
        return self.excinfo

    def _unroll_exceptions(
        self, exceptions: Iterable[BaseException]
    ) -> Iterable[BaseException]:
        """Used in non-strict mode."""
        res: list[BaseException] = []
        for exc in exceptions:
            if isinstance(exc, BaseExceptionGroup):
                res.extend(self._unroll_exceptions(exc.exceptions))

            else:
                res.append(exc)
        return res

    def matches(
        self,
        exc_val: BaseException | None,
    ) -> TypeGuard[BaseExceptionGroup[E]]:
        """Check if an exception matches the requirements of this RaisesGroup.

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
        if exc_val is None:
            return False
        # TODO: print/raise why a match fails, in a way that works properly in nested cases
        # maybe have a list of strings logging failed matches, that __exit__ can
        # recursively step through and print on a failing match.
        if not isinstance(exc_val, BaseExceptionGroup):
            return False
        if len(exc_val.exceptions) != len(self.expected_exceptions):
            return False
        if self.match_expr is not None and not re.search(
            self.match_expr, _stringify_exception(exc_val)
        ):
            return False
        if self.check is not None and not self.check(exc_val):
            return False
        remaining_exceptions = list(self.expected_exceptions)
        actual_exceptions: Iterable[BaseException] = exc_val.exceptions
        if not self.strict:
            actual_exceptions = self._unroll_exceptions(actual_exceptions)

        # it should be possible to get RaisesGroup.matches typed so as not to
        # need these type: ignores, but I'm not sure that's possible while also having it
        # transparent for the end user.
        for e in actual_exceptions:
            for rem_e in remaining_exceptions:
                if (
                    (isinstance(rem_e, type) and isinstance(e, rem_e))
                    or (
                        isinstance(e, BaseExceptionGroup)
                        and isinstance(rem_e, RaisesGroup)
                        and rem_e.matches(e)
                    )
                    or (isinstance(rem_e, Matcher) and rem_e.matches(e))
                ):
                    remaining_exceptions.remove(rem_e)  # type: ignore[arg-type]
                    break
            else:
                return False
        return True

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

        if not self.matches(exc_val):
            return False

        # Cast to narrow the exception type now that it's verified.
        exc_info = cast(
            "tuple[type[BaseExceptionGroup[E]], BaseExceptionGroup[E], types.TracebackType]",
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
