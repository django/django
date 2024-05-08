import signal
import sys
import types
from typing import Any, TypeVar

import pytest

import trio
from trio.testing import Matcher, RaisesGroup

from .. import _core
from .._core._tests.tutil import (
    create_asyncio_future_in_new_loop,
    ignore_coroutine_never_awaited_warnings,
)
from .._util import (
    ConflictDetector,
    NoPublicConstructor,
    coroutine_or_error,
    final,
    fixup_module_metadata,
    generic_function,
    is_main_thread,
    signal_raise,
)
from ..testing import wait_all_tasks_blocked

T = TypeVar("T")


def test_signal_raise() -> None:
    record = []

    def handler(signum: int, _: object) -> None:
        record.append(signum)

    old = signal.signal(signal.SIGFPE, handler)
    try:
        signal_raise(signal.SIGFPE)
    finally:
        signal.signal(signal.SIGFPE, old)
    assert record == [signal.SIGFPE]


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
            # not bothering to type this one
            @asyncio.coroutine  # type: ignore[misc]
            def generator_based_coro() -> Any:  # pragma: no cover
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

        async def async_gen(_: object) -> Any:  # pragma: no cover
            yield

        # does not give arg-type typing error
        with pytest.raises(TypeError) as excinfo:
            coroutine_or_error(async_gen, [0])  # type: ignore[unused-coroutine]
        msg = "expected an async function but got an async generator"
        assert msg in str(excinfo.value)

        # Make sure no references are kept around to keep anything alive
        del excinfo


def test_generic_function() -> None:
    @generic_function  # Decorated function contains "Any".
    def test_func(arg: T) -> T:  # type: ignore[misc]
        """Look, a docstring!"""
        return arg

    assert test_func is test_func[int] is test_func[int, str]
    assert test_func(42) == test_func[int](42) == 42
    assert test_func.__doc__ == "Look, a docstring!"
    assert test_func.__qualname__ == "test_generic_function.<locals>.test_func"  # type: ignore[attr-defined]
    assert test_func.__name__ == "test_func"  # type: ignore[attr-defined]
    assert test_func.__module__ == __name__


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
            assert b == 3.14

    with pytest.raises(TypeError):
        SpecialClass(8, 3.14)

    # Private constructor should not raise, and passes args to __init__.
    assert isinstance(SpecialClass._create(8, b=3.14), SpecialClass)


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
    mod.SomeClass.recursion = mod.SomeClass  # type: ignore[attr-defined]

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

    assert mod.SomeClass.method.__name__ == "method"  # type: ignore[attr-defined]
    assert mod.SomeClass.method.__module__ == "trio.somemodule"  # type: ignore[attr-defined]
    assert mod.SomeClass.method.__qualname__ == "SomeClass.method"  # type: ignore[attr-defined]
    # Make coverage happy.
    non_trio_module.some_func()  # type: ignore[no-untyped-call]
    mod.some_func()  # type: ignore[no-untyped-call]
    mod._private()  # type: ignore[no-untyped-call]
    mod.SomeClass().method()
