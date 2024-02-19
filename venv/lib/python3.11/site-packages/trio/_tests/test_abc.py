from __future__ import annotations

import attr
import pytest

from .. import abc as tabc
from ..lowlevel import Task


def test_instrument_implements_hook_methods() -> None:
    attrs = {
        "before_run": (),
        "after_run": (),
        "task_spawned": (Task,),
        "task_scheduled": (Task,),
        "before_task_step": (Task,),
        "after_task_step": (Task,),
        "task_exited": (Task,),
        "before_io_wait": (3.3,),
        "after_io_wait": (3.3,),
    }

    mayonnaise = tabc.Instrument()

    for method_name, args in attrs.items():
        assert hasattr(mayonnaise, method_name)
        method = getattr(mayonnaise, method_name)
        assert callable(method)
        method(*args)


async def test_AsyncResource_defaults() -> None:
    @attr.s
    class MyAR(tabc.AsyncResource):
        record: list[str] = attr.ib(factory=list)

        async def aclose(self) -> None:
            self.record.append("ac")

    async with MyAR() as myar:
        assert isinstance(myar, MyAR)
        assert myar.record == []

    assert myar.record == ["ac"]


def test_abc_generics() -> None:
    # Pythons below 3.5.2 had a typing.Generic that would throw
    # errors when instantiating or subclassing a parameterized
    # version of a class with any __slots__. This is why RunVar
    # (which has slots) is not generic. This tests that
    # the generic ABCs are fine, because while they are slotted
    # they don't actually define any slots.

    class SlottedChannel(tabc.SendChannel[tabc.Stream]):
        __slots__ = ("x",)

        def send_nowait(self, value: object) -> None:
            raise RuntimeError

        async def send(self, value: object) -> None:
            raise RuntimeError  # pragma: no cover

        def clone(self) -> None:
            raise RuntimeError  # pragma: no cover

        async def aclose(self) -> None:
            pass  # pragma: no cover

    channel = SlottedChannel()
    with pytest.raises(RuntimeError):
        channel.send_nowait(None)
