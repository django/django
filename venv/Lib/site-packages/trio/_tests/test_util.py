from __future__ import annotations

import sys
import types
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Coroutine, Generator
import pytest

import trio
from trio.testing import _Matcher as Matcher, _RaisesGroup as RaisesGroup

from .. import _core
from .._core._tests.tutil import (
    create_asyncio_future_in_new_loop,
    ignore_coroutine_never_awaited_warnings,
)
from .._util import (
    ConflictDetector,
    MultipleExceptionError,
    NoPublicConstructor,
    coroutine_or_error,
    final,
    fixup_module_metadata,
    is_main_thread,
    raise_single_exception_from_group,
)
from ..testing import wait_all_tasks_blocked

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

T = TypeVar("T")


async def test_ConflictDetector() -> None:
    ul1 = ConflictDetector("ul1")
    ul2 = ConflictDetector("ul2")

    with ul1:
        with ul2:
            print("ok")

    with pytest.raises(_core.BusyResourceError, match="ul1"):
        with ul1:
            with ul1:
                pass  # pragma: no cover

    async def wait_with_ul1() -> None:
        with ul1:
            await wait_all_tasks_blocked()

    with RaisesGroup(Matcher(_core.BusyResourceError, "ul1")):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(wait_with_ul1)
            nursery.start_soon(wait_with_ul1)


def test_module_metadata_is_fixed_up() -> None:
    import trio
    import trio.testing

    assert trio.Cancelled.__module__ == "trio"
    assert trio.open_nursery.__module__ == "trio"
    assert trio.abc.Stream.__module__ == "trio.abc"
    assert trio.lowlevel.wait_task_rescheduled.__module__ == "trio.lowlevel"
    assert trio.testing.trio_test.__module__ == "trio.testing"

    # Also check methods
    assert trio.lowlevel.ParkingLot.__init__.__module__ == "trio.lowlevel"
    assert trio.abc.Stream.send_all.__module__ == "trio.abc"

    # And names
    assert trio.Cancelled.__name__ == "Cancelled"
    assert trio.Cancelled.__qualname__ == "Cancelled"
    assert trio.abc.SendStream.send_all.__name__ == "send_all"
    assert trio.abc.SendStream.send_all.__qualname__ == "SendStream.send_all"
    assert trio.to_thread.__name__ == "trio.to_thread"
    assert trio.to_thread.run_sync.__name__ == "run_sync"
    assert trio.to_thread.run_sync.__qualname__ == "run_sync"


async def test_is_main_thread() -> None:
    assert is_main_thread()

    def not_main_thread() -> None:
        assert not is_main_thread()

    await trio.to_thread.run_sync(not_main_thread)


# @coroutine is deprecated since python 3.8, which is fine with us.
@pytest.mark.filterwarnings("ignore:.*@coroutine.*:DeprecationWarning")
def test_coroutine_or_error() -> None:
    class Deferred:
        "Just kidding"

    with ignore_coroutine_never_awaited_warnings():

        async def f() -> None:  # pragma: no cover
            pass

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(f())  # type: ignore[arg-type, unused-coroutine]
        assert "expecting an async function" in str(excinfo.value)

        import asyncio

        if sys.version_info < (3, 11):

            @asyncio.coroutine
            def generator_based_coro() -> (
                Generator[Coroutine[None, None, None], None, None]
            ):  # pragma: no cover
                yield from asyncio.sleep(1)

            with pytest.raises(TypeError) as excinfo:
                coroutine_or_error(generator_based_coro())  # type: ignore[arg-type, unused-coroutine]
            assert "asyncio" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(create_asyncio_future_in_new_loop())  # type: ignore[arg-type, unused-coroutine]
        assert "asyncio" in str(excinfo.value)

        # does not raise arg-type error
        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(create_asyncio_future_in_new_loop)  # type: ignore[unused-coroutine]
        assert "asyncio" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(Deferred())  # type: ignore[arg-type, unused-coroutine]
        assert "twisted" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(lambda: Deferred())  # type: ignore[arg-type, unused-coroutine, return-value]
        assert "twisted" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(len, [[1, 2, 3]])  # type: ignore[arg-type, unused-coroutine]

        assert "appears to be synchronous" in str(excinfo.value)

        async def async_gen(
            _: object,
        ) -> AsyncGenerator[None, None]:  # pragma: no cover
            yield

        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(async_gen, [0])  # type: ignore[arg-type,unused-coroutine]
        msg = "expected an async function but got an async generator"
        assert msg in str(excinfo.value)

        # Make sure no references are kept around to keep anything alive
        del excinfo


def test_final_decorator() -> None:
    """Test that subclassing a @final-annotated class is not allowed.

    This checks both runtime results, and verifies that type checkers detect
    the error statically through the type-ignore comment.
    """

    @final
    class FinalClass:
        pass

    with pytest.raises(TypeError):

        class SubClass(FinalClass):  # type: ignore[misc]
            pass


def test_no_public_constructor_metaclass() -> None:
    """The NoPublicConstructor metaclass prevents calling the constructor directly."""

    class SpecialClass(metaclass=NoPublicConstructor):
        def __init__(self, a: int, b: float) -> None:
            """Check arguments can be passed to __init__."""
            assert a == 8
            assert b == 3.15

    with pytest.raises(TypeError):
        SpecialClass(8, 3.15)

    # Private constructor should not raise, and passes args to __init__.
    assert isinstance(SpecialClass._create(8, b=3.15), SpecialClass)


def test_fixup_module_metadata() -> None:
    # Ignores modules not in the trio.X tree.
    non_trio_module = types.ModuleType("not_trio")
    non_trio_module.some_func = lambda: None  # type: ignore[attr-defined]
    non_trio_module.some_func.__name__ = "some_func"
    non_trio_module.some_func.__qualname__ = "some_func"

    fixup_module_metadata(non_trio_module.__name__, vars(non_trio_module))

    assert non_trio_module.some_func.__name__ == "some_func"
    assert non_trio_module.some_func.__qualname__ == "some_func"

    # Bulild up a fake module to test. Just use lambdas since all we care about is the names.
    mod = types.ModuleType("trio._somemodule_impl")
    mod.some_func = lambda: None  # type: ignore[attr-defined]
    mod.some_func.__name__ = "_something_else"
    mod.some_func.__qualname__ = "_something_else"

    # No __module__ means it's unchanged.
    mod.not_funclike = types.SimpleNamespace()  # type: ignore[attr-defined]
    mod.not_funclike.__name__ = "not_funclike"

    # Check __qualname__ being absent works.
    mod.only_has_name = types.SimpleNamespace()  # type: ignore[attr-defined]
    mod.only_has_name.__module__ = "trio._somemodule_impl"
    mod.only_has_name.__name__ = "only_name"

    # Underscored names are unchanged.
    mod._private = lambda: None  # type: ignore[attr-defined]
    mod._private.__module__ = "trio._somemodule_impl"
    mod._private.__name__ = mod._private.__qualname__ = "_private"

    # We recurse into classes.
    mod.SomeClass = type(  # type: ignore[attr-defined]
        "SomeClass",
        (),
        {
            "__init__": lambda self: None,
            "method": lambda self: None,
        },
    )
    # Reference loop is fine.
    mod.SomeClass.recursion = mod.SomeClass

    fixup_module_metadata("trio.somemodule", vars(mod))
    assert mod.some_func.__name__ == "some_func"
    assert mod.some_func.__module__ == "trio.somemodule"
    assert mod.some_func.__qualname__ == "some_func"

    assert mod.not_funclike.__name__ == "not_funclike"
    assert mod._private.__name__ == "_private"
    assert mod._private.__module__ == "trio._somemodule_impl"
    assert mod._private.__qualname__ == "_private"

    assert mod.only_has_name.__name__ == "only_has_name"
    assert mod.only_has_name.__module__ == "trio.somemodule"
    assert not hasattr(mod.only_has_name, "__qualname__")

    assert mod.SomeClass.method.__name__ == "method"
    assert mod.SomeClass.method.__module__ == "trio.somemodule"
    assert mod.SomeClass.method.__qualname__ == "SomeClass.method"
    # Make coverage happy.
    non_trio_module.some_func()
    mod.some_func()
    mod._private()
    mod.SomeClass().method()


async def test_raise_single_exception_from_group() -> None:
    excinfo: pytest.ExceptionInfo[BaseException]

    exc = ValueError("foo")
    cause = SyntaxError("cause")
    context = TypeError("context")
    exc.__cause__ = cause
    exc.__context__ = context
    cancelled = trio.Cancelled._create(source="deadline")

    with pytest.raises(ValueError, match="foo") as excinfo:
        raise_single_exception_from_group(ExceptionGroup("", [exc]))
    assert excinfo.value.__cause__ == cause
    assert excinfo.value.__context__ == context

    # only unwraps one layer of exceptiongroup
    inner_eg = ExceptionGroup("inner eg", [exc])
    inner_cause = SyntaxError("inner eg cause")
    inner_context = TypeError("inner eg context")
    inner_eg.__cause__ = inner_cause
    inner_eg.__context__ = inner_context
    with RaisesGroup(Matcher(ValueError, match="^foo$"), match="^inner eg$") as eginfo:
        raise_single_exception_from_group(ExceptionGroup("", [inner_eg]))
    assert eginfo.value.__cause__ == inner_cause
    assert eginfo.value.__context__ == inner_context

    with pytest.raises(ValueError, match="foo") as excinfo:
        raise_single_exception_from_group(
            BaseExceptionGroup("", [cancelled, cancelled, exc])
        )
    assert excinfo.value.__cause__ == cause
    assert excinfo.value.__context__ == context

    # multiple non-cancelled
    eg = ExceptionGroup("", [ValueError("foo"), ValueError("bar")])
    with pytest.raises(
        MultipleExceptionError,
        match=r"^Attempted to unwrap exceptiongroup with multiple non-cancelled exceptions. This is often caused by a bug in the caller.$",
    ) as excinfo:
        raise_single_exception_from_group(eg)
    assert excinfo.value.__cause__ is eg
    assert excinfo.value.__context__ is None

    # keyboardinterrupt overrides everything
    eg_ki = BaseExceptionGroup(
        "",
        [
            ValueError("foo"),
            ValueError("bar"),
            KeyboardInterrupt("preserve error msg"),
        ],
    )
    with pytest.raises(
        KeyboardInterrupt,
        match=r"^preserve error msg$",
    ) as excinfo:
        raise_single_exception_from_group(eg_ki)

    assert excinfo.value.__cause__ is eg_ki
    assert excinfo.value.__context__ is None

    # and same for SystemExit but verify code too
    systemexit_ki = BaseExceptionGroup(
        "",
        [
            ValueError("foo"),
            ValueError("bar"),
            SystemExit(2),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        raise_single_exception_from_group(systemexit_ki)

    assert excinfo.value.code == 2
    assert excinfo.value.__cause__ is systemexit_ki
    assert excinfo.value.__context__ is None

    # if we only got cancelled, first one is reraised
    with pytest.raises(trio.Cancelled, match=r"^cancelled due to deadline$") as excinfo:
        raise_single_exception_from_group(
            BaseExceptionGroup(
                "", [cancelled, trio.Cancelled._create(source="explicit")]
            )
        )
    assert excinfo.value is cancelled
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None
