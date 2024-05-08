from __future__ import annotations

from typing import TYPE_CHECKING, Container, Iterable, NoReturn

import attrs
import pytest

from ... import _abc, _core
from .tutil import check_sequence_matches

if TYPE_CHECKING:
    from ...lowlevel import Task


@attrs.define(eq=False, hash=False, slots=False)
class TaskRecorder(_abc.Instrument):
    record: list[tuple[str, Task | None]] = attrs.Factory(list)

    def before_run(self) -> None:
        self.record.append(("before_run", None))

    def task_scheduled(self, task: Task) -> None:
        self.record.append(("schedule", task))

    def before_task_step(self, task: Task) -> None:
        assert task is _core.current_task()
        self.record.append(("before", task))

    def after_task_step(self, task: Task) -> None:
        assert task is _core.current_task()
        self.record.append(("after", task))

    def after_run(self) -> None:
        self.record.append(("after_run", None))

    def filter_tasks(self, tasks: Container[Task]) -> Iterable[tuple[str, Task | None]]:
        for item in self.record:
            if item[0] in ("schedule", "before", "after") and item[1] in tasks:
                yield item
            if item[0] in ("before_run", "after_run"):
                yield item


def test_instruments(recwarn: object) -> None:
    r1 = TaskRecorder()
    r2 = TaskRecorder()
    r3 = TaskRecorder()

    task = None

    # We use a child task for this, because the main task does some extra
    # bookkeeping stuff that can leak into the instrument results, and we
    # don't want to deal with it.
    async def task_fn() -> None:
        nonlocal task
        task = _core.current_task()

        for _ in range(4):
            await _core.checkpoint()
        # replace r2 with r3, to test that we can manipulate them as we go
        _core.remove_instrument(r2)
        with pytest.raises(KeyError):
            _core.remove_instrument(r2)
        # add is idempotent
        _core.add_instrument(r3)
        _core.add_instrument(r3)
        for _ in range(1):
            await _core.checkpoint()

    async def main() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(task_fn)

    _core.run(main, instruments=[r1, r2])

    # It sleeps 5 times, so it runs 6 times.  Note that checkpoint()
    # reschedules the task immediately upon yielding, before the
    # after_task_step event fires.
    expected = (
        [("before_run", None), ("schedule", task)]
        + [("before", task), ("schedule", task), ("after", task)] * 5
        + [("before", task), ("after", task), ("after_run", None)]
    )
    assert r1.record == r2.record + r3.record
    assert task is not None
    assert list(r1.filter_tasks([task])) == expected


def test_instruments_interleave() -> None:
    tasks = {}

    async def two_step1() -> None:
        tasks["t1"] = _core.current_task()
        await _core.checkpoint()

    async def two_step2() -> None:
        tasks["t2"] = _core.current_task()
        await _core.checkpoint()

    async def main() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(two_step1)
            nursery.start_soon(two_step2)

    r = TaskRecorder()
    _core.run(main, instruments=[r])

    expected = [
        ("before_run", None),
        ("schedule", tasks["t1"]),
        ("schedule", tasks["t2"]),
        {
            ("before", tasks["t1"]),
            ("schedule", tasks["t1"]),
            ("after", tasks["t1"]),
            ("before", tasks["t2"]),
            ("schedule", tasks["t2"]),
            ("after", tasks["t2"]),
        },
        {
            ("before", tasks["t1"]),
            ("after", tasks["t1"]),
            ("before", tasks["t2"]),
            ("after", tasks["t2"]),
        },
        ("after_run", None),
    ]
    print(list(r.filter_tasks(tasks.values())))
    check_sequence_matches(list(r.filter_tasks(tasks.values())), expected)


def test_null_instrument() -> None:
    # undefined instrument methods are skipped
    class NullInstrument(_abc.Instrument):
        def something_unrelated(self) -> None:
            pass  # pragma: no cover

    async def main() -> None:
        await _core.checkpoint()

    _core.run(main, instruments=[NullInstrument()])


def test_instrument_before_after_run() -> None:
    record = []

    class BeforeAfterRun(_abc.Instrument):
        def before_run(self) -> None:
            record.append("before_run")

        def after_run(self) -> None:
            record.append("after_run")

    async def main() -> None:
        pass

    _core.run(main, instruments=[BeforeAfterRun()])
    assert record == ["before_run", "after_run"]


def test_instrument_task_spawn_exit() -> None:
    record = []

    class SpawnExitRecorder(_abc.Instrument):
        def task_spawned(self, task: Task) -> None:
            record.append(("spawned", task))

        def task_exited(self, task: Task) -> None:
            record.append(("exited", task))

    async def main() -> Task:
        return _core.current_task()

    main_task = _core.run(main, instruments=[SpawnExitRecorder()])
    assert ("spawned", main_task) in record
    assert ("exited", main_task) in record


# This test also tests having a crash before the initial task is even spawned,
# which is very difficult to handle.
def test_instruments_crash(caplog: pytest.LogCaptureFixture) -> None:
    record = []

    class BrokenInstrument(_abc.Instrument):
        def task_scheduled(self, task: Task) -> NoReturn:
            record.append("scheduled")
            raise ValueError("oops")

        def close(self) -> None:
            # Shouldn't be called -- tests that the instrument disabling logic
            # works right.
            record.append("closed")  # pragma: no cover

    async def main() -> Task:
        record.append("main ran")
        return _core.current_task()

    r = TaskRecorder()
    main_task = _core.run(main, instruments=[r, BrokenInstrument()])
    assert record == ["scheduled", "main ran"]
    # the TaskRecorder kept going throughout, even though the BrokenInstrument
    # was disabled
    assert ("after", main_task) in r.record
    assert ("after_run", None) in r.record
    # And we got a log message
    assert caplog.records[0].exc_info is not None
    exc_type, exc_value, exc_traceback = caplog.records[0].exc_info
    assert exc_type is ValueError
    assert str(exc_value) == "oops"
    assert "Instrument has been disabled" in caplog.records[0].message


def test_instruments_monkeypatch() -> None:
    class NullInstrument(_abc.Instrument):
        pass

    instrument = NullInstrument()

    async def main() -> None:
        record: list[Task] = []

        # Changing the set of hooks implemented by an instrument after
        # it's installed doesn't make them start being called right away
        instrument.before_task_step = (  # type: ignore[method-assign]
            record.append  # type: ignore[assignment] # append is pos-only
        )

        await _core.checkpoint()
        await _core.checkpoint()
        assert len(record) == 0

        # But if we remove and re-add the instrument, the new hooks are
        # picked up
        _core.remove_instrument(instrument)
        _core.add_instrument(instrument)
        await _core.checkpoint()
        await _core.checkpoint()
        assert record.count(_core.current_task()) == 2

        _core.remove_instrument(instrument)
        await _core.checkpoint()
        await _core.checkpoint()
        assert record.count(_core.current_task()) == 2

    _core.run(main, instruments=[instrument])


def test_instrument_that_raises_on_getattr() -> None:
    class EvilInstrument(_abc.Instrument):
        def task_exited(self, task: Task) -> NoReturn:
            raise AssertionError("this should never happen")  # pragma: no cover

        @property
        def after_run(self) -> NoReturn:
            raise ValueError("oops")

    async def main() -> None:
        with pytest.raises(ValueError, match="^oops$"):
            _core.add_instrument(EvilInstrument())

        # Make sure the instrument is fully removed from the per-method lists
        runner = _core.current_task()._runner
        assert "after_run" not in runner.instruments
        assert "task_exited" not in runner.instruments

    _core.run(main)
