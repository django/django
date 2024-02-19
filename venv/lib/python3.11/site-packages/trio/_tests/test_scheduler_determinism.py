from __future__ import annotations

from typing import TYPE_CHECKING

import trio

if TYPE_CHECKING:
    import pytest


async def scheduler_trace() -> tuple[tuple[str, int], ...]:
    """Returns a scheduler-dependent value we can use to check determinism."""
    trace = []

    async def tracer(name: str) -> None:
        for i in range(50):
            trace.append((name, i))
            await trio.sleep(0)

    async with trio.open_nursery() as nursery:
        for i in range(5):
            nursery.start_soon(tracer, str(i))

    return tuple(trace)


def test_the_trio_scheduler_is_not_deterministic() -> None:
    # At least, not yet.  See https://github.com/python-trio/trio/issues/32
    traces = []
    for _ in range(10):
        traces.append(trio.run(scheduler_trace))
    assert len(set(traces)) == len(traces)


def test_the_trio_scheduler_is_deterministic_if_seeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(trio._core._run, "_ALLOW_DETERMINISTIC_SCHEDULING", True)
    traces = []
    for _ in range(10):
        state = trio._core._run._r.getstate()
        try:
            trio._core._run._r.seed(0)
            traces.append(trio.run(scheduler_trace))
        finally:
            trio._core._run._r.setstate(state)

    assert len(traces) == 10
    assert len(set(traces)) == 1
