from __future__ import annotations

import contextlib
import sys
import weakref
from math import inf
from typing import TYPE_CHECKING, NoReturn

import pytest

from ... import _core
from .tutil import gc_collect_harder, restore_unraisablehook

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def test_asyncgen_basics() -> None:
    collected = []

    async def example(cause: str) -> AsyncGenerator[int, None]:
        try:
            with contextlib.suppress(GeneratorExit):
                yield 42
            await _core.checkpoint()
        except _core.Cancelled:
            assert "exhausted" not in cause
            task_name = _core.current_task().name
            assert cause in task_name or task_name == "<init>"
            assert _core.current_effective_deadline() == -inf
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            collected.append(cause)
        else:
            assert "async_main" in _core.current_task().name
            assert "exhausted" in cause
            assert _core.current_effective_deadline() == inf
            await _core.checkpoint()
            collected.append(cause)

    saved = []

    async def async_main() -> None:
        # GC'ed before exhausted
        with pytest.warns(
            ResourceWarning, match="Async generator.*collected before.*exhausted"
        ):
            assert await example("abandoned").asend(None) == 42
            gc_collect_harder()
        await _core.wait_all_tasks_blocked()
        assert collected.pop() == "abandoned"

        aiter_ = example("exhausted 1")
        try:
            assert await aiter_.asend(None) == 42
        finally:
            await aiter_.aclose()
        assert collected.pop() == "exhausted 1"

        # Also fine if you exhaust it at point of use
        async for val in example("exhausted 2"):
            assert val == 42
        assert collected.pop() == "exhausted 2"

        gc_collect_harder()

        # No problems saving the geniter when using either of these patterns
        aiter_ = example("exhausted 3")
        try:
            saved.append(aiter_)
            assert await aiter_.asend(None) == 42
        finally:
            await aiter_.aclose()
        assert collected.pop() == "exhausted 3"

        # Also fine if you exhaust it at point of use
        saved.append(example("exhausted 4"))
        async for val in saved[-1]:
            assert val == 42
        assert collected.pop() == "exhausted 4"

        # Leave one referenced-but-unexhausted and make sure it gets cleaned up
        saved.append(example("outlived run"))
        assert await saved[-1].asend(None) == 42
        assert collected == []

    _core.run(async_main)
    assert collected.pop() == "outlived run"
    for agen in saved:
        assert agen.ag_frame is None  # all should now be exhausted


async def test_asyncgen_throws_during_finalization(
    caplog: pytest.LogCaptureFixture,
) -> None:
    record = []

    async def agen() -> AsyncGenerator[int, None]:
        try:
            yield 1
        finally:
            await _core.cancel_shielded_checkpoint()
            record.append("crashing")
            raise ValueError("oops")

    with restore_unraisablehook():
        await agen().asend(None)
        gc_collect_harder()
    await _core.wait_all_tasks_blocked()
    assert record == ["crashing"]
    # Following type ignore is because typing for LogCaptureFixture is wrong
    exc_type, exc_value, exc_traceback = caplog.records[0].exc_info  # type: ignore[misc]
    assert exc_type is ValueError
    assert str(exc_value) == "oops"
    assert "during finalization of async generator" in caplog.records[0].message


def test_firstiter_after_closing() -> None:
    saved = []
    record = []

    async def funky_agen() -> AsyncGenerator[int, None]:
        try:
            yield 1
        except GeneratorExit:
            record.append("cleanup 1")
            raise
        try:
            yield 2
        finally:
            record.append("cleanup 2")
            await funky_agen().asend(None)

    async def async_main() -> None:
        aiter_ = funky_agen()
        saved.append(aiter_)
        assert await aiter_.asend(None) == 1
        assert await aiter_.asend(None) == 2

    _core.run(async_main)
    assert record == ["cleanup 2", "cleanup 1"]


def test_interdependent_asyncgen_cleanup_order() -> None:
    saved: list[AsyncGenerator[int, None]] = []
    record: list[int | str] = []

    async def innermost() -> AsyncGenerator[int, None]:
        try:
            yield 1
        finally:
            await _core.cancel_shielded_checkpoint()
            record.append("innermost")

    async def agen(
        label: int, inner: AsyncGenerator[int, None]
    ) -> AsyncGenerator[int, None]:
        try:
            yield await inner.asend(None)
        finally:
            # Either `inner` has already been cleaned up, or
            # we're about to exhaust it. Either way, we wind
            # up with `record` containing the labels in
            # innermost-to-outermost order.
            with pytest.raises(StopAsyncIteration):
                await inner.asend(None)
            record.append(label)

    async def async_main() -> None:
        # This makes a chain of 101 interdependent asyncgens:
        # agen(99)'s cleanup will iterate agen(98)'s will iterate
        # ... agen(0)'s will iterate innermost()'s
        ag_chain = innermost()
        for idx in range(100):
            ag_chain = agen(idx, ag_chain)
        saved.append(ag_chain)
        assert await ag_chain.asend(None) == 1
        assert record == []

    _core.run(async_main)
    assert record == ["innermost", *range(100)]


@restore_unraisablehook()
def test_last_minute_gc_edge_case() -> None:
    saved: list[AsyncGenerator[int, None]] = []
    record = []
    needs_retry = True

    async def agen() -> AsyncGenerator[int, None]:
        try:
            yield 1
        finally:
            record.append("cleaned up")

    def collect_at_opportune_moment(token: _core._entry_queue.TrioToken) -> None:
        runner = _core._run.GLOBAL_RUN_CONTEXT.runner
        assert runner.system_nursery is not None
        if runner.system_nursery._closed and isinstance(
            runner.asyncgens.alive, weakref.WeakSet
        ):
            saved.clear()
            record.append("final collection")
            gc_collect_harder()
            record.append("done")
        else:
            try:
                token.run_sync_soon(collect_at_opportune_moment, token)
            except _core.RunFinishedError:  # pragma: no cover
                nonlocal needs_retry
                needs_retry = True

    async def async_main() -> None:
        token = _core.current_trio_token()
        token.run_sync_soon(collect_at_opportune_moment, token)
        saved.append(agen())
        await saved[-1].asend(None)

    # Actually running into the edge case requires that the run_sync_soon task
    # execute in between the system nursery's closure and the strong-ification
    # of runner.asyncgens. There's about a 25% chance that it doesn't
    # (if the run_sync_soon task runs before init on one tick and after init
    # on the next tick); if we try enough times, we can make the chance of
    # failure as small as we want.
    for _attempt in range(50):
        needs_retry = False
        del record[:]
        del saved[:]
        _core.run(async_main)
        if needs_retry:  # pragma: no cover
            assert record == ["cleaned up"]
        else:
            assert record == ["final collection", "done", "cleaned up"]
            break
    else:  # pragma: no cover
        pytest.fail(
            "Didn't manage to hit the trailing_finalizer_asyncgens case "
            f"despite trying {_attempt} times"
        )


async def step_outside_async_context(aiter_: AsyncGenerator[int, None]) -> None:
    # abort_fns run outside of task context, at least if they're
    # triggered by a deadline expiry rather than a direct
    # cancellation.  Thus, an asyncgen first iterated inside one
    # will appear non-Trio, and since no other hooks were installed,
    # will use the last-ditch fallback handling (that tries to mimic
    # CPython's behavior with no hooks).
    #
    # NB: the strangeness with aiter being an attribute of abort_fn is
    # to make it as easy as possible to ensure we don't hang onto a
    # reference to aiter inside the guts of the run loop.
    def abort_fn(_: _core.RaiseCancelT) -> _core.Abort:
        with pytest.raises(StopIteration, match="42"):
            abort_fn.aiter.asend(None).send(None)  # type: ignore[attr-defined]  # Callables don't have attribute "aiter"
        del abort_fn.aiter  # type: ignore[attr-defined]
        return _core.Abort.SUCCEEDED

    abort_fn.aiter = aiter_  # type: ignore[attr-defined]

    async with _core.open_nursery() as nursery:
        nursery.start_soon(_core.wait_task_rescheduled, abort_fn)
        await _core.wait_all_tasks_blocked()
        nursery.cancel_scope.deadline = _core.current_time()


async def test_fallback_when_no_hook_claims_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def well_behaved() -> AsyncGenerator[int, None]:
        yield 42

    async def yields_after_yield() -> AsyncGenerator[int, None]:
        with pytest.raises(GeneratorExit):
            yield 42
        yield 100

    async def awaits_after_yield() -> AsyncGenerator[int, None]:
        with pytest.raises(GeneratorExit):
            yield 42
        await _core.cancel_shielded_checkpoint()

    with restore_unraisablehook():
        await step_outside_async_context(well_behaved())
        gc_collect_harder()
        assert capsys.readouterr().err == ""

        await step_outside_async_context(yields_after_yield())
        gc_collect_harder()
        assert "ignored GeneratorExit" in capsys.readouterr().err

        await step_outside_async_context(awaits_after_yield())
        gc_collect_harder()
        assert "awaited something during finalization" in capsys.readouterr().err


def test_delegation_to_existing_hooks() -> None:
    record = []

    def my_firstiter(agen: AsyncGenerator[object, NoReturn]) -> None:
        record.append("firstiter " + agen.ag_frame.f_locals["arg"])

    def my_finalizer(agen: AsyncGenerator[object, NoReturn]) -> None:
        record.append("finalizer " + agen.ag_frame.f_locals["arg"])

    async def example(arg: str) -> AsyncGenerator[int, None]:
        try:
            yield 42
        finally:
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            record.append("trio collected " + arg)

    async def async_main() -> None:
        await step_outside_async_context(example("theirs"))
        assert await example("ours").asend(None) == 42
        gc_collect_harder()
        assert record == ["firstiter theirs", "finalizer theirs"]
        record[:] = []
        await _core.wait_all_tasks_blocked()
        assert record == ["trio collected ours"]

    with restore_unraisablehook():
        old_hooks = sys.get_asyncgen_hooks()
        sys.set_asyncgen_hooks(my_firstiter, my_finalizer)
        try:
            _core.run(async_main)
        finally:
            assert sys.get_asyncgen_hooks() == (my_firstiter, my_finalizer)
            sys.set_asyncgen_hooks(*old_hooks)
