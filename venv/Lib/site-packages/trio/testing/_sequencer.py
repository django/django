from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import attrs

from .. import Event, _core, _util

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@_util.final
@attrs.define(eq=False, slots=False)
class Sequencer:
    """A convenience class for forcing code in different tasks to run in an
    explicit linear order.

    Instances of this class implement a ``__call__`` method which returns an
    async context manager. The idea is that you pass a sequence number to
    ``__call__`` to say where this block of code should go in the linear
    sequence. Block 0 starts immediately, and then block N doesn't start until
    block N-1 has finished.

    Example:
      An extremely elaborate way to print the numbers 0-5, in order::

         async def worker1(seq):
             async with seq(0):
                 print(0)
             async with seq(4):
                 print(4)

         async def worker2(seq):
             async with seq(2):
                 print(2)
             async with seq(5):
                 print(5)

         async def worker3(seq):
             async with seq(1):
                 print(1)
             async with seq(3):
                 print(3)

         async def main():
            seq = trio.testing.Sequencer()
            async with trio.open_nursery() as nursery:
                nursery.start_soon(worker1, seq)
                nursery.start_soon(worker2, seq)
                nursery.start_soon(worker3, seq)

    """

    _sequence_points: defaultdict[int, Event] = attrs.field(
        factory=lambda: defaultdict(Event),
        init=False,
    )
    _claimed: set[int] = attrs.field(factory=set, init=False)
    _broken: bool = attrs.field(default=False, init=False)

    @asynccontextmanager
    async def __call__(self, position: int) -> AsyncIterator[None]:
        if position in self._claimed:
            raise RuntimeError(f"Attempted to reuse sequence point {position}")
        if self._broken:
            raise RuntimeError("sequence broken!")
        self._claimed.add(position)
        if position != 0:
            try:
                await self._sequence_points[position].wait()
            except _core.Cancelled:
                self._broken = True
                for event in self._sequence_points.values():
                    event.set()
                raise RuntimeError(
                    "Sequencer wait cancelled -- sequence broken",
                ) from None
            else:
                if self._broken:
                    raise RuntimeError("sequence broken!")
        try:
            yield
        finally:
            self._sequence_points[position + 1].set()
