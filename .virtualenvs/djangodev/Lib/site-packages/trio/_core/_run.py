from __future__ import annotations

import enum
import functools
import gc
import itertools
import random
import select
import sys
import threading
import warnings
from collections import deque
from contextlib import AbstractAsyncContextManager, contextmanager, suppress
from contextvars import copy_context
from heapq import heapify, heappop, heappush
from math import inf
from time import perf_counter
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    NoReturn,
    Protocol,
    TypeVar,
    cast,
    overload,
)

import attrs
from outcome import Error, Outcome, Value, capture
from sniffio import thread_local as sniffio_library
from sortedcontainers import SortedDict

from .. import _core
from .._abc import Clock, Instrument
from .._deprecate import warn_deprecated
from .._util import NoPublicConstructor, coroutine_or_error, final
from ._asyncgens import AsyncGenerators
from ._concat_tb import concat_tb
from ._entry_queue import EntryQueue, TrioToken
from ._exceptions import Cancelled, RunFinishedError, TrioInternalError
from ._instrumentation import Instruments
from ._ki import LOCALS_KEY_KI_PROTECTION_ENABLED, KIManager, enable_ki_protection
from ._thread_cache import start_thread_soon
from ._traps import (
    Abort,
    CancelShieldedCheckpoint,
    PermanentlyDetachCoroutineObject,
    WaitTaskRescheduled,
    cancel_shielded_checkpoint,
    wait_task_rescheduled,
)

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

FnT = TypeVar("FnT", bound="Callable[..., Any]")
StatusT = TypeVar("StatusT")
StatusT_co = TypeVar("StatusT_co", covariant=True)
StatusT_contra = TypeVar("StatusT_contra", contravariant=True)
RetT = TypeVar("RetT")


if TYPE_CHECKING:
    import contextvars
    import types
    from collections.abc import (
        Awaitable,
        Callable,
        Coroutine,
        Generator,
        Iterator,
        Sequence,
    )
    from types import TracebackType

    # for some strange reason Sphinx works with outcome.Outcome, but not Outcome, in
    # start_guest_run. Same with types.FrameType in iter_await_frames
    import outcome
    from typing_extensions import Self, TypeVarTuple, Unpack

    PosArgT = TypeVarTuple("PosArgT")


DEADLINE_HEAP_MIN_PRUNE_THRESHOLD: Final = 1000

# Passed as a sentinel
_NO_SEND: Final[Outcome[Any]] = cast("Outcome[Any]", object())

# Used to track if an exceptiongroup can be collapsed
NONSTRICT_EXCEPTIONGROUP_NOTE = 'This is a "loose" ExceptionGroup, and may be collapsed by Trio if it only contains one exception - typically after `Cancelled` has been stripped from it. Note this has consequences for exception handling, and strict_exception_groups=True is recommended.'


@final
class _NoStatus(metaclass=NoPublicConstructor):
    """Sentinel for unset TaskStatus._value."""


# Decorator to mark methods public. This does nothing by itself, but
# trio/_tools/gen_exports.py looks for it.
def _public(fn: FnT) -> FnT:
    return fn


# When running under Hypothesis, we want examples to be reproducible and
# shrinkable.  pytest-trio's Hypothesis integration monkeypatches this
# variable to True, and registers the Random instance _r for Hypothesis
# to manage for each test case, which together should make Trio's task
# scheduling loop deterministic.  We have a test for that, of course.
_ALLOW_DETERMINISTIC_SCHEDULING: Final = False
_r = random.Random()


def _count_context_run_tb_frames() -> int:
    """Count implementation dependent traceback frames from Context.run()

    On CPython, Context.run() is implemented in C and doesn't show up in
    tracebacks. On PyPy, it is implemented in Python and adds 1 frame to
    tracebacks.

    Returns:
        int: Traceback frame count

    """

    def function_with_unique_name_xyzzy() -> NoReturn:
        try:
            1 / 0  # noqa: B018  # We need a ZeroDivisionError to fire
        except ZeroDivisionError:
            raise
        else:  # pragma: no cover
            raise TrioInternalError(
                "A ZeroDivisionError should have been raised, but it wasn't."
            )

    ctx = copy_context()
    try:
        ctx.run(function_with_unique_name_xyzzy)
    except ZeroDivisionError as exc:
        tb = exc.__traceback__
        # Skip the frame where we caught it
        tb = tb.tb_next  # type: ignore[union-attr]
        count = 0
        while tb.tb_frame.f_code.co_name != "function_with_unique_name_xyzzy":  # type: ignore[union-attr]
            tb = tb.tb_next  # type: ignore[union-attr]
            count += 1
        return count
    else:  # pragma: no cover
        raise TrioInternalError(
            f"The purpose of {function_with_unique_name_xyzzy.__name__} is "
            "to raise a ZeroDivisionError, but it didn't."
        )


CONTEXT_RUN_TB_FRAMES: Final = _count_context_run_tb_frames()


@attrs.frozen
class SystemClock(Clock):
    # Add a large random offset to our clock to ensure that if people
    # accidentally call time.perf_counter() directly or start comparing clocks
    # between different runs, then they'll notice the bug quickly:
    offset: float = attrs.Factory(lambda: _r.uniform(10000, 200000))

    def start_clock(self) -> None:
        pass

    # In cPython 3, on every platform except Windows, perf_counter is
    # exactly the same as time.monotonic; and on Windows, it uses
    # QueryPerformanceCounter instead of GetTickCount64.
    def current_time(self) -> float:
        return self.offset + perf_counter()

    def deadline_to_sleep_time(self, deadline: float) -> float:
        return deadline - self.current_time()


class IdlePrimedTypes(enum.Enum):
    WAITING_FOR_IDLE = 1
    AUTOJUMP_CLOCK = 2


################################################################
# CancelScope and friends
################################################################


def collapse_exception_group(
    excgroup: BaseExceptionGroup[BaseException],
) -> BaseException:
    """Recursively collapse any single-exception groups into that single contained
    exception.

    """
    exceptions = list(excgroup.exceptions)
    modified = False
    for i, exc in enumerate(exceptions):
        if isinstance(exc, BaseExceptionGroup):
            new_exc = collapse_exception_group(exc)
            if new_exc is not exc:
                modified = True
                exceptions[i] = new_exc

    if (
        len(exceptions) == 1
        and isinstance(excgroup, BaseExceptionGroup)
        and NONSTRICT_EXCEPTIONGROUP_NOTE in getattr(excgroup, "__notes__", ())
    ):
        exceptions[0].__traceback__ = concat_tb(
            excgroup.__traceback__, exceptions[0].__traceback__
        )
        return exceptions[0]
    elif modified:
        return excgroup.derive(exceptions)
    else:
        return excgroup


@attrs.define(eq=False)
class Deadlines:
    """A container of deadlined cancel scopes.

    Only contains scopes with non-infinite deadlines that are currently
    attached to at least one task.

    """

    # Heap of (deadline, id(CancelScope), CancelScope)
    _heap: list[tuple[float, int, CancelScope]] = attrs.Factory(list)
    # Count of active deadlines (those that haven't been changed)
    _active: int = 0

    def add(self, deadline: float, cancel_scope: CancelScope) -> None:
        heappush(self._heap, (deadline, id(cancel_scope), cancel_scope))
        self._active += 1

    def remove(self, deadline: float, cancel_scope: CancelScope) -> None:
        self._active -= 1

    def next_deadline(self) -> float:
        while self._heap:
            deadline, _, cancel_scope = self._heap[0]
            if deadline == cancel_scope._registered_deadline:
                return deadline
            else:
                # This entry is stale; discard it and try again
                heappop(self._heap)
        return inf

    def _prune(self) -> None:
        # In principle, it's possible for a cancel scope to toggle back and
        # forth repeatedly between the same two deadlines, and end up with
        # lots of stale entries that *look* like they're still active, because
        # their deadline is correct, but in fact are redundant. So when
        # pruning we have to eliminate entries with the wrong deadline, *and*
        # eliminate duplicates.
        seen = set()
        pruned_heap = []
        for deadline, tiebreaker, cancel_scope in self._heap:
            if deadline == cancel_scope._registered_deadline:
                if cancel_scope in seen:
                    continue
                seen.add(cancel_scope)
                pruned_heap.append((deadline, tiebreaker, cancel_scope))
        # See test_cancel_scope_deadline_duplicates for a test that exercises
        # this assert:
        assert len(pruned_heap) == self._active
        heapify(pruned_heap)
        self._heap = pruned_heap

    def expire(self, now: float) -> bool:
        did_something = False
        while self._heap and self._heap[0][0] <= now:
            deadline, _, cancel_scope = heappop(self._heap)
            if deadline == cancel_scope._registered_deadline:
                did_something = True
                # This implicitly calls self.remove(), so we don't need to
                # decrement _active here
                cancel_scope.cancel()
        # If we've accumulated too many stale entries, then prune the heap to
        # keep it under control. (We only do this occasionally in a batch, to
        # keep the amortized cost down)
        if len(self._heap) > self._active * 2 + DEADLINE_HEAP_MIN_PRUNE_THRESHOLD:
            self._prune()
        return did_something


@attrs.define(eq=False)
class CancelStatus:
    """Tracks the cancellation status for a contiguous extent
    of code that will become cancelled, or not, as a unit.

    Each task has at all times a single "active" CancelStatus whose
    cancellation state determines whether checkpoints executed in that
    task raise Cancelled. Each 'with CancelScope(...)' context is
    associated with a particular CancelStatus.  When a task enters
    such a context, a CancelStatus is created which becomes the active
    CancelStatus for that task; when the 'with' block is exited, the
    active CancelStatus for that task goes back to whatever it was
    before.

    CancelStatus objects are arranged in a tree whose structure
    mirrors the lexical nesting of the cancel scope contexts.  When a
    CancelStatus becomes cancelled, it notifies all of its direct
    children, who become cancelled in turn (and continue propagating
    the cancellation down the tree) unless they are shielded. (There
    will be at most one such child except in the case of a
    CancelStatus that immediately encloses a nursery.) At the leaves
    of this tree are the tasks themselves, which get woken up to deliver
    an abort when their direct parent CancelStatus becomes cancelled.

    You can think of CancelStatus as being responsible for the
    "plumbing" of cancellations as oppposed to CancelScope which is
    responsible for the origination of them.

    """

    # Our associated cancel scope. Can be any object with attributes
    # `deadline`, `shield`, and `cancel_called`, but in current usage
    # is always a CancelScope object. Must not be None.
    _scope: CancelScope = attrs.field(alias="scope")

    # True iff the tasks in self._tasks should receive cancellations
    # when they checkpoint. Always True when scope.cancel_called is True;
    # may also be True due to a cancellation propagated from our
    # parent.  Unlike scope.cancel_called, this does not necessarily stay
    # true once it becomes true. For example, we might become
    # effectively cancelled due to the cancel scope two levels out
    # becoming cancelled, but then the cancel scope one level out
    # becomes shielded so we're not effectively cancelled anymore.
    effectively_cancelled: bool = False

    # The CancelStatus whose cancellations can propagate to us; we
    # become effectively cancelled when they do, unless scope.shield
    # is True.  May be None (for the outermost CancelStatus in a call
    # to trio.run(), briefly during TaskStatus.started(), or during
    # recovery from mis-nesting of cancel scopes).
    _parent: CancelStatus | None = attrs.field(default=None, repr=False, alias="parent")

    # All of the CancelStatuses that have this CancelStatus as their parent.
    _children: set[CancelStatus] = attrs.field(factory=set, init=False, repr=False)

    # Tasks whose cancellation state is currently tied directly to
    # the cancellation state of this CancelStatus object. Don't modify
    # this directly; instead, use Task._activate_cancel_status().
    # Invariant: all(task._cancel_status is self for task in self._tasks)
    _tasks: set[Task] = attrs.field(factory=set, init=False, repr=False)

    # Set to True on still-active cancel statuses that are children
    # of a cancel status that's been closed. This is used to permit
    # recovery from mis-nested cancel scopes (well, at least enough
    # recovery to show a useful traceback).
    abandoned_by_misnesting: bool = attrs.field(default=False, init=False, repr=False)

    def __attrs_post_init__(self) -> None:
        if self._parent is not None:
            self._parent._children.add(self)
            self.recalculate()

    # parent/children/tasks accessors are used by TaskStatus.started()

    @property
    def parent(self) -> CancelStatus | None:
        return self._parent

    @parent.setter
    def parent(self, parent: CancelStatus) -> None:
        if self._parent is not None:
            self._parent._children.remove(self)
        self._parent = parent
        if self._parent is not None:
            self._parent._children.add(self)
            self.recalculate()

    @property
    def children(self) -> frozenset[CancelStatus]:
        return frozenset(self._children)

    @property
    def tasks(self) -> frozenset[Task]:
        return frozenset(self._tasks)

    def encloses(self, other: CancelStatus | None) -> bool:
        """Returns true if this cancel status is a direct or indirect
        parent of cancel status *other*, or if *other* is *self*.
        """
        while other is not None:
            if other is self:
                return True
            other = other.parent
        return False

    def close(self) -> None:
        self.parent = None  # now we're not a child of self.parent anymore
        if self._tasks or self._children:
            # Cancel scopes weren't exited in opposite order of being
            # entered. CancelScope._close() deals with raising an error
            # if appropriate; our job is to leave things in a reasonable
            # state for unwinding our dangling children. We choose to leave
            # this part of the CancelStatus tree unlinked from everyone
            # else, cancelled, and marked so that exiting a CancelScope
            # within the abandoned subtree doesn't affect the active
            # CancelStatus. Note that it's possible for us to get here
            # without CancelScope._close() raising an error, if a
            # nursery's cancel scope is closed within the nursery's
            # nested child and no other cancel scopes are involved,
            # but in that case task_exited() will deal with raising
            # the error.
            self._mark_abandoned()

            # Since our CancelScope is about to forget about us, and we
            # have no parent anymore, there's nothing left to call
            # recalculate(). So, we can stay cancelled by setting
            # effectively_cancelled and updating our children.
            self.effectively_cancelled = True
            for task in self._tasks:
                task._attempt_delivery_of_any_pending_cancel()
            for child in self._children:
                child.recalculate()

    @property
    def parent_cancellation_is_visible_to_us(self) -> bool:
        return (
            self._parent is not None
            and not self._scope.shield
            and self._parent.effectively_cancelled
        )

    def recalculate(self) -> None:
        # This does a depth-first traversal over this and descendent cancel
        # statuses, to ensure their state is up-to-date. It's basically a
        # recursive algorithm, but we use an explicit stack to avoid any
        # issues with stack overflow.
        todo = [self]
        while todo:
            current = todo.pop()
            new_state = (
                current._scope.cancel_called
                or current.parent_cancellation_is_visible_to_us
            )
            if new_state != current.effectively_cancelled:
                current.effectively_cancelled = new_state
                if new_state:
                    for task in current._tasks:
                        task._attempt_delivery_of_any_pending_cancel()
                todo.extend(current._children)

    def _mark_abandoned(self) -> None:
        self.abandoned_by_misnesting = True
        for child in self._children:
            child._mark_abandoned()

    def effective_deadline(self) -> float:
        if self.effectively_cancelled:
            return -inf
        if self._parent is None or self._scope.shield:
            return self._scope.deadline
        return min(self._scope.deadline, self._parent.effective_deadline())


MISNESTING_ADVICE = """
This is probably a bug in your code, that has caused Trio's internal state to
become corrupted. We'll do our best to recover, but from now on there are
no guarantees.

Typically this is caused by one of the following:
  - yielding within a generator or async generator that's opened a cancel
    scope or nursery (unless the generator is a @contextmanager or
    @asynccontextmanager); see https://github.com/python-trio/trio/issues/638
  - manually calling __enter__ or __exit__ on a trio.CancelScope, or
    __aenter__ or __aexit__ on the object returned by trio.open_nursery();
    doing so correctly is difficult and you should use @[async]contextmanager
    instead, or maybe [Async]ExitStack
  - using [Async]ExitStack to interleave the entries/exits of cancel scopes
    and/or nurseries in a way that couldn't be achieved by some nesting of
    'with' and 'async with' blocks
  - using the low-level coroutine object protocol to execute some parts of
    an async function in a different cancel scope/nursery context than
    other parts
If you don't believe you're doing any of these things, please file a bug:
https://github.com/python-trio/trio/issues/new
"""


@final
@attrs.define(eq=False, repr=False)
class CancelScope:
    """A *cancellation scope*: the link between a unit of cancellable
    work and Trio's cancellation system.

    A :class:`CancelScope` becomes associated with some cancellable work
    when it is used as a context manager surrounding that work::

        cancel_scope = trio.CancelScope()
        ...
        with cancel_scope:
            await long_running_operation()

    Inside the ``with`` block, a cancellation of ``cancel_scope`` (via
    a call to its :meth:`cancel` method or via the expiry of its
    :attr:`deadline`) will immediately interrupt the
    ``long_running_operation()`` by raising :exc:`Cancelled` at its
    next :ref:`checkpoint <checkpoints>`.

    The context manager ``__enter__`` returns the :class:`CancelScope`
    object itself, so you can also write ``with trio.CancelScope() as
    cancel_scope:``.

    If a cancel scope becomes cancelled before entering its ``with`` block,
    the :exc:`Cancelled` exception will be raised at the first
    checkpoint inside the ``with`` block. This allows a
    :class:`CancelScope` to be created in one :ref:`task <tasks>` and
    passed to another, so that the first task can later cancel some work
    inside the second.

    Cancel scopes are not reusable or reentrant; that is, each cancel
    scope can be used for at most one ``with`` block.  (You'll get a
    :exc:`RuntimeError` if you violate this rule.)

    The :class:`CancelScope` constructor takes initial values for the
    cancel scope's :attr:`deadline` and :attr:`shield` attributes; these
    may be freely modified after construction, whether or not the scope
    has been entered yet, and changes take immediate effect.
    """

    _cancel_status: CancelStatus | None = attrs.field(default=None, init=False)
    _has_been_entered: bool = attrs.field(default=False, init=False)
    _registered_deadline: float = attrs.field(default=inf, init=False)
    _cancel_called: bool = attrs.field(default=False, init=False)
    cancelled_caught: bool = attrs.field(default=False, init=False)

    # Constructor arguments:
    _deadline: float = attrs.field(default=inf, kw_only=True, alias="deadline")
    _shield: bool = attrs.field(default=False, kw_only=True, alias="shield")

    @enable_ki_protection
    def __enter__(self) -> Self:
        task = _core.current_task()
        if self._has_been_entered:
            raise RuntimeError(
                "Each CancelScope may only be used for a single 'with' block"
            )
        self._has_been_entered = True
        if current_time() >= self._deadline:
            self.cancel()
        with self._might_change_registered_deadline():
            self._cancel_status = CancelStatus(scope=self, parent=task._cancel_status)
            task._activate_cancel_status(self._cancel_status)
        return self

    def _close(self, exc: BaseException | None) -> BaseException | None:
        if self._cancel_status is None:
            new_exc = RuntimeError(
                f"Cancel scope stack corrupted: attempted to exit {self!r} "
                "which had already been exited"
            )
            new_exc.__context__ = exc
            return new_exc
        scope_task = current_task()
        if scope_task._cancel_status is not self._cancel_status:
            # Cancel scope mis-nesting: this cancel scope isn't the most
            # recently opened by this task (that's still open). That is,
            # our assumptions about context managers forming a stack
            # have been violated. Try and make the best of it.
            if self._cancel_status.abandoned_by_misnesting:
                # We are an inner cancel scope that was still active when
                # some outer scope was closed. The closure of that outer
                # scope threw an error, so we don't need to throw another
                # one; it would just confuse the traceback.
                pass
            elif not self._cancel_status.encloses(scope_task._cancel_status):
                # This task isn't even indirectly contained within the
                # cancel scope it's trying to close. Raise an error
                # without changing any state.
                new_exc = RuntimeError(
                    f"Cancel scope stack corrupted: attempted to exit {self!r} "
                    f"from unrelated {scope_task!r}\n{MISNESTING_ADVICE}"
                )
                new_exc.__context__ = exc
                return new_exc
            else:
                # Otherwise, there's some inner cancel scope(s) that
                # we're abandoning by closing this outer one.
                # CancelStatus.close() will take care of the plumbing;
                # we just need to make sure we don't let the error
                # pass silently.
                new_exc = RuntimeError(
                    f"Cancel scope stack corrupted: attempted to exit {self!r} "
                    f"in {scope_task!r} that's still within its child {scope_task._cancel_status._scope!r}\n{MISNESTING_ADVICE}"
                )
                new_exc.__context__ = exc
                exc = new_exc
                scope_task._activate_cancel_status(self._cancel_status.parent)
        else:
            scope_task._activate_cancel_status(self._cancel_status.parent)
        if (
            exc is not None
            and self._cancel_status.effectively_cancelled
            and not self._cancel_status.parent_cancellation_is_visible_to_us
        ):
            if isinstance(exc, Cancelled):
                self.cancelled_caught = True
                exc = None
            elif isinstance(exc, BaseExceptionGroup):
                matched, exc = exc.split(Cancelled)
                if matched:
                    self.cancelled_caught = True

                if exc:
                    exc = collapse_exception_group(exc)

        self._cancel_status.close()
        with self._might_change_registered_deadline():
            self._cancel_status = None
        return exc

    def __exit__(
        self,
        etype: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        # NB: NurseryManager calls _close() directly rather than __exit__(),
        # so __exit__() must be just _close() plus this logic for adapting
        # the exception-filtering result to the context manager API.

        # This inlines the enable_ki_protection decorator so we can fix
        # f_locals *locally* below to avoid reference cycles
        locals()[LOCALS_KEY_KI_PROTECTION_ENABLED] = True

        # Tracebacks show the 'raise' line below out of context, so let's give
        # this variable a name that makes sense out of context.
        remaining_error_after_cancel_scope = self._close(exc)
        if remaining_error_after_cancel_scope is None:
            return True
        elif remaining_error_after_cancel_scope is exc:
            return False
        else:
            # Copied verbatim from the old MultiErrorCatcher.  Python doesn't
            # allow us to encapsulate this __context__ fixup.
            old_context = remaining_error_after_cancel_scope.__context__
            try:
                raise remaining_error_after_cancel_scope
            finally:
                _, value, _ = sys.exc_info()
                assert value is remaining_error_after_cancel_scope
                value.__context__ = old_context
                # delete references from locals to avoid creating cycles
                # see test_cancel_scope_exit_doesnt_create_cyclic_garbage
                # Note: still relevant
                del remaining_error_after_cancel_scope, value, _, exc
                # deep magic to remove refs via f_locals
                locals()
                # TODO: check if PEP558 changes the need for this call
                # https://github.com/python/cpython/pull/3640

    def __repr__(self) -> str:
        if self._cancel_status is not None:
            binding = "active"
        elif self._has_been_entered:
            binding = "exited"
        else:
            binding = "unbound"

        if self._cancel_called:
            state = ", cancelled"
        elif self._deadline == inf:
            state = ""
        else:
            try:
                now = current_time()
            except RuntimeError:  # must be called from async context
                state = ""
            else:
                state = ", deadline is {:.2f} seconds {}".format(
                    abs(self._deadline - now),
                    "from now" if self._deadline >= now else "ago",
                )

        return f"<trio.CancelScope at {id(self):#x}, {binding}{state}>"

    @contextmanager
    @enable_ki_protection
    def _might_change_registered_deadline(self) -> Iterator[None]:
        try:
            yield
        finally:
            old = self._registered_deadline
            if self._cancel_status is None or self._cancel_called:
                new = inf
            else:
                new = self._deadline
            if old != new:
                self._registered_deadline = new
                runner = GLOBAL_RUN_CONTEXT.runner
                if runner.is_guest:
                    old_next_deadline = runner.deadlines.next_deadline()
                if old != inf:
                    runner.deadlines.remove(old, self)
                if new != inf:
                    runner.deadlines.add(new, self)
                if runner.is_guest:
                    new_next_deadline = runner.deadlines.next_deadline()
                    if old_next_deadline != new_next_deadline:
                        runner.force_guest_tick_asap()

    @property
    def deadline(self) -> float:
        """Read-write, :class:`float`. An absolute time on the current
        run's clock at which this scope will automatically become
        cancelled. You can adjust the deadline by modifying this
        attribute, e.g.::

           # I need a little more time!
           cancel_scope.deadline += 30

        Note that for efficiency, the core run loop only checks for
        expired deadlines every once in a while. This means that in
        certain cases there may be a short delay between when the clock
        says the deadline should have expired, and when checkpoints
        start raising :exc:`~trio.Cancelled`. This is a very obscure
        corner case that you're unlikely to notice, but we document it
        for completeness. (If this *does* cause problems for you, of
        course, then `we want to know!
        <https://github.com/python-trio/trio/issues>`__)

        Defaults to :data:`math.inf`, which means "no deadline", though
        this can be overridden by the ``deadline=`` argument to
        the :class:`~trio.CancelScope` constructor.
        """
        return self._deadline

    @deadline.setter
    def deadline(self, new_deadline: float) -> None:
        with self._might_change_registered_deadline():
            self._deadline = float(new_deadline)

    @property
    def shield(self) -> bool:
        """Read-write, :class:`bool`, default :data:`False`. So long as
        this is set to :data:`True`, then the code inside this scope
        will not receive :exc:`~trio.Cancelled` exceptions from scopes
        that are outside this scope. They can still receive
        :exc:`~trio.Cancelled` exceptions from (1) this scope, or (2)
        scopes inside this scope. You can modify this attribute::

           with trio.CancelScope() as cancel_scope:
               cancel_scope.shield = True
               # This cannot be interrupted by any means short of
               # killing the process:
               await sleep(10)

               cancel_scope.shield = False
               # Now this can be cancelled normally:
               await sleep(10)

        Defaults to :data:`False`, though this can be overridden by the
        ``shield=`` argument to the :class:`~trio.CancelScope` constructor.
        """
        return self._shield

    @shield.setter
    @enable_ki_protection
    def shield(self, new_value: bool) -> None:
        if not isinstance(new_value, bool):
            raise TypeError("shield must be a bool")
        self._shield = new_value
        if self._cancel_status is not None:
            self._cancel_status.recalculate()

    @enable_ki_protection
    def cancel(self) -> None:
        """Cancels this scope immediately.

        This method is idempotent, i.e., if the scope was already
        cancelled then this method silently does nothing.
        """
        if self._cancel_called:
            return
        with self._might_change_registered_deadline():
            self._cancel_called = True
        if self._cancel_status is not None:
            self._cancel_status.recalculate()

    @property
    def cancel_called(self) -> bool:
        """Readonly :class:`bool`. Records whether cancellation has been
        requested for this scope, either by an explicit call to
        :meth:`cancel` or by the deadline expiring.

        This attribute being True does *not* necessarily mean that the
        code within the scope has been, or will be, affected by the
        cancellation. For example, if :meth:`cancel` was called after
        the last checkpoint in the ``with`` block, when it's too late to
        deliver a :exc:`~trio.Cancelled` exception, then this attribute
        will still be True.

        This attribute is mostly useful for debugging and introspection.
        If you want to know whether or not a chunk of code was actually
        cancelled, then :attr:`cancelled_caught` is usually more
        appropriate.
        """
        if (  # noqa: SIM102  # collapsible-if but this way is nicer
            self._cancel_status is not None or not self._has_been_entered
        ):
            # Scope is active or not yet entered: make sure cancel_called
            # is true if the deadline has passed. This shouldn't
            # be able to actually change behavior, since we check for
            # deadline expiry on scope entry and at every checkpoint,
            # but it makes the value returned by cancel_called more
            # closely match expectations.
            if not self._cancel_called and current_time() >= self._deadline:
                self.cancel()
        return self._cancel_called


################################################################
# Nursery and friends
################################################################


class TaskStatus(Protocol[StatusT_contra]):
    """The interface provided by :meth:`Nursery.start()` to the spawned task.

    This is provided via the ``task_status`` keyword-only parameter.
    """

    @overload
    def started(self: TaskStatus[None]) -> None: ...

    @overload
    def started(self, value: StatusT_contra) -> None: ...

    def started(self, value: StatusT_contra | None = None) -> None:
        """Tasks call this method to indicate that they have initialized.

        See `nursery.start() <trio.Nursery.start>` for more information.
        """


# This code needs to be read alongside the code from Nursery.start to make
# sense.
@attrs.define(eq=False, hash=False, repr=False, slots=False)
class _TaskStatus(TaskStatus[StatusT]):
    _old_nursery: Nursery
    _new_nursery: Nursery
    # NoStatus is a sentinel.
    _value: StatusT | type[_NoStatus] = _NoStatus

    def __repr__(self) -> str:
        return f"<Task status object at {id(self):#x}>"

    @overload
    def started(self: _TaskStatus[None]) -> None: ...

    @overload
    def started(self: _TaskStatus[StatusT], value: StatusT) -> None: ...

    def started(self, value: StatusT | None = None) -> None:
        if self._value is not _NoStatus:
            raise RuntimeError("called 'started' twice on the same task status")
        self._value = cast(StatusT, value)  # If None, StatusT == None

        # If the old nursery is cancelled, then quietly quit now; the child
        # will eventually exit on its own, and we don't want to risk moving
        # children that might have propagating Cancelled exceptions into
        # a place with no cancelled cancel scopes to catch them.
        assert self._old_nursery._cancel_status is not None
        if self._old_nursery._cancel_status.effectively_cancelled:
            return

        # Can't be closed, b/c we checked in start() and then _pending_starts
        # should keep it open.
        assert not self._new_nursery._closed

        # Move tasks from the old nursery to the new
        tasks = self._old_nursery._children
        self._old_nursery._children = set()
        for task in tasks:
            task._parent_nursery = self._new_nursery
            task._eventual_parent_nursery = None
            self._new_nursery._children.add(task)

        # Move all children of the old nursery's cancel status object
        # to be underneath the new nursery instead. This includes both
        # tasks and child cancel status objects.
        # NB: If the new nursery is cancelled, reparenting a cancel
        # status to be underneath it can invoke an abort_fn, which might
        # do something evil like cancel the old nursery. We thus break
        # everything off from the old nursery before we start attaching
        # anything to the new.
        cancel_status_children = self._old_nursery._cancel_status.children
        cancel_status_tasks = set(self._old_nursery._cancel_status.tasks)
        cancel_status_tasks.discard(self._old_nursery._parent_task)
        for cancel_status in cancel_status_children:
            cancel_status.parent = None
        for task in cancel_status_tasks:
            task._activate_cancel_status(None)
        for cancel_status in cancel_status_children:
            cancel_status.parent = self._new_nursery._cancel_status
        for task in cancel_status_tasks:
            task._activate_cancel_status(self._new_nursery._cancel_status)

        # That should have removed all the children from the old nursery
        assert not self._old_nursery._children

        # And finally, poke the old nursery so it notices that all its
        # children have disappeared and can exit.
        self._old_nursery._check_nursery_closed()


@attrs.define(slots=False)
class NurseryManager:
    """Nursery context manager.

    Note we explicitly avoid @asynccontextmanager and @async_generator
    since they add a lot of extraneous stack frames to exceptions, as
    well as cause problematic behavior with handling of StopIteration
    and StopAsyncIteration.

    """

    strict_exception_groups: bool = True

    @enable_ki_protection
    async def __aenter__(self) -> Nursery:
        self._scope = CancelScope()
        self._scope.__enter__()
        self._nursery = Nursery._create(
            current_task(), self._scope, self.strict_exception_groups
        )
        return self._nursery

    @enable_ki_protection
    async def __aexit__(
        self,
        etype: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        new_exc = await self._nursery._nested_child_finished(exc)
        # Tracebacks show the 'raise' line below out of context, so let's give
        # this variable a name that makes sense out of context.
        combined_error_from_nursery = self._scope._close(new_exc)
        if combined_error_from_nursery is None:
            return True
        elif combined_error_from_nursery is exc:
            return False
        else:
            # Copied verbatim from the old MultiErrorCatcher.  Python doesn't
            # allow us to encapsulate this __context__ fixup.
            old_context = combined_error_from_nursery.__context__
            try:
                raise combined_error_from_nursery
            finally:
                _, value, _ = sys.exc_info()
                assert value is combined_error_from_nursery
                value.__context__ = old_context
                # delete references from locals to avoid creating cycles
                # see test_cancel_scope_exit_doesnt_create_cyclic_garbage
                del _, combined_error_from_nursery, value, new_exc

    # make sure these raise errors in static analysis if called
    if not TYPE_CHECKING:

        def __enter__(self) -> NoReturn:
            raise RuntimeError(
                "use 'async with open_nursery(...)', not 'with open_nursery(...)'"
            )

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> NoReturn:  # pragma: no cover
            raise AssertionError("Never called, but should be defined")


def open_nursery(
    strict_exception_groups: bool | None = None,
) -> AbstractAsyncContextManager[Nursery]:
    """Returns an async context manager which must be used to create a
    new `Nursery`.

    It does not block on entry; on exit it blocks until all child tasks
    have exited.

    Args:
      strict_exception_groups (bool): Unless set to False, even a single raised exception
          will be wrapped in an exception group. If not specified, uses the value passed
          to :func:`run`, which defaults to true. Setting it to False will be deprecated
          and ultimately removed in a future version of Trio.

    """
    # only warn if explicitly set to falsy, not if we get it from the global context.
    if strict_exception_groups is not None and not strict_exception_groups:
        warn_deprecated(
            "open_nursery(strict_exception_groups=False)",
            version="0.24.1",
            issue=2929,
            instead="the default value of True and rewrite exception handlers to handle ExceptionGroups",
        )

    if strict_exception_groups is None:
        strict_exception_groups = GLOBAL_RUN_CONTEXT.runner.strict_exception_groups

    return NurseryManager(strict_exception_groups=strict_exception_groups)


@final
class Nursery(metaclass=NoPublicConstructor):
    """A context which may be used to spawn (or cancel) child tasks.

    Not constructed directly, use `open_nursery` instead.

    The nursery will remain open until all child tasks have completed,
    or until it is cancelled, at which point it will cancel all its
    remaining child tasks and close.

    Nurseries ensure the absence of orphaned Tasks, since all running
    tasks will belong to an open Nursery.

    Attributes:
        cancel_scope:
            Creating a nursery also implicitly creates a cancellation scope,
            which is exposed as the :attr:`cancel_scope` attribute. This is
            used internally to implement the logic where if an error occurs
            then ``__aexit__`` cancels all children, but you can use it for
            other things, e.g. if you want to explicitly cancel all children
            in response to some external event.
    """

    def __init__(
        self,
        parent_task: Task,
        cancel_scope: CancelScope,
        strict_exception_groups: bool,
    ):
        self._parent_task = parent_task
        self._strict_exception_groups = strict_exception_groups
        parent_task._child_nurseries.append(self)
        # the cancel status that children inherit - we take a snapshot, so it
        # won't be affected by any changes in the parent.
        self._cancel_status = parent_task._cancel_status
        # the cancel scope that directly surrounds us; used for cancelling all
        # children.
        self.cancel_scope = cancel_scope
        assert self.cancel_scope._cancel_status is self._cancel_status
        self._children: set[Task] = set()
        self._pending_excs: list[BaseException] = []
        # The "nested child" is how this code refers to the contents of the
        # nursery's 'async with' block, which acts like a child Task in all
        # the ways we can make it.
        self._nested_child_running = True
        self._parent_waiting_in_aexit = False
        self._pending_starts = 0
        self._closed = False

    @property
    def child_tasks(self) -> frozenset[Task]:
        """(`frozenset`): Contains all the child :class:`~trio.lowlevel.Task`
        objects which are still running."""
        return frozenset(self._children)

    @property
    def parent_task(self) -> Task:
        "(`~trio.lowlevel.Task`):  The Task that opened this nursery."
        return self._parent_task

    def _add_exc(self, exc: BaseException) -> None:
        self._pending_excs.append(exc)
        self.cancel_scope.cancel()

    def _check_nursery_closed(self) -> None:
        if not any([self._nested_child_running, self._children, self._pending_starts]):
            self._closed = True
            if self._parent_waiting_in_aexit:
                self._parent_waiting_in_aexit = False
                GLOBAL_RUN_CONTEXT.runner.reschedule(self._parent_task)

    def _child_finished(self, task: Task, outcome: Outcome[Any]) -> None:
        self._children.remove(task)
        if isinstance(outcome, Error):
            self._add_exc(outcome.error)
        self._check_nursery_closed()

    async def _nested_child_finished(
        self, nested_child_exc: BaseException | None
    ) -> BaseException | None:
        # Returns ExceptionGroup instance (or any exception if the nursery is in loose mode
        # and there is just one contained exception) if there are pending exceptions
        if nested_child_exc is not None:
            self._add_exc(nested_child_exc)
        self._nested_child_running = False
        self._check_nursery_closed()

        if not self._closed:
            # If we have a KeyboardInterrupt injected, we want to save it in
            # the nursery's final exceptions list. But if it's just a
            # Cancelled, then we don't -- see gh-1457.
            def aborted(raise_cancel: _core.RaiseCancelT) -> Abort:
                exn = capture(raise_cancel).error
                if not isinstance(exn, Cancelled):
                    self._add_exc(exn)
                # see test_cancel_scope_exit_doesnt_create_cyclic_garbage
                del exn  # prevent cyclic garbage creation
                return Abort.FAILED

            self._parent_waiting_in_aexit = True
            await wait_task_rescheduled(aborted)
        else:
            # Nothing to wait for, so execute a schedule point, but don't
            # allow us to be cancelled, just like the other branch.  We
            # still need to catch and store non-Cancelled exceptions.
            try:
                await cancel_shielded_checkpoint()
            except BaseException as exc:
                self._add_exc(exc)

        popped = self._parent_task._child_nurseries.pop()
        assert popped is self
        if self._pending_excs:
            try:
                if not self._strict_exception_groups and len(self._pending_excs) == 1:
                    return self._pending_excs[0]
                exception = BaseExceptionGroup(
                    "Exceptions from Trio nursery", self._pending_excs
                )
                if not self._strict_exception_groups:
                    exception.add_note(NONSTRICT_EXCEPTIONGROUP_NOTE)
                return exception
            finally:
                # avoid a garbage cycle
                # (see test_locals_destroyed_promptly_on_cancel)
                del self._pending_excs
        return None

    def start_soon(
        self,
        async_fn: Callable[[Unpack[PosArgT]], Awaitable[object]],
        *args: Unpack[PosArgT],
        name: object = None,
    ) -> None:
        """Creates a child task, scheduling ``await async_fn(*args)``.

        If you want to run a function and immediately wait for its result,
        then you don't need a nursery; just use ``await async_fn(*args)``.
        If you want to wait for the task to initialize itself before
        continuing, see :meth:`start`, the other fundamental method for
        creating concurrent tasks in Trio.

        Note that this is *not* an async function and you don't use await
        when calling it. It sets up the new task, but then returns
        immediately, *before* the new task has a chance to do anything.
        New tasks may start running in any order, and at any checkpoint the
        scheduler chooses - at latest when the nursery is waiting to exit.

        It's possible to pass a nursery object into another task, which
        allows that task to start new child tasks in the first task's
        nursery.

        The child task inherits its parent nursery's cancel scopes.

        Args:
            async_fn: An async callable.
            args: Positional arguments for ``async_fn``. If you want
                  to pass keyword arguments, use
                  :func:`functools.partial`.
            name: The name for this task. Only used for
                  debugging/introspection
                  (e.g. ``repr(task_obj)``). If this isn't a string,
                  :meth:`start_soon` will try to make it one. A
                  common use case is if you're wrapping a function
                  before spawning a new task, you might pass the
                  original function as the ``name=`` to make
                  debugging easier.

        Raises:
            RuntimeError: If this nursery is no longer open
                          (i.e. its ``async with`` block has
                          exited).
        """
        GLOBAL_RUN_CONTEXT.runner.spawn_impl(async_fn, args, self, name)

    async def start(
        self,
        async_fn: Callable[..., Awaitable[object]],
        *args: object,
        name: object = None,
    ) -> Any:
        r"""Creates and initializes a child task.

        Like :meth:`start_soon`, but blocks until the new task has
        finished initializing itself, and optionally returns some
        information from it.

        The ``async_fn`` must accept a ``task_status`` keyword argument,
        and it must make sure that it (or someone) eventually calls
        :meth:`task_status.started() <TaskStatus.started>`.

        The conventional way to define ``async_fn`` is like::

            async def async_fn(arg1, arg2, *, task_status=trio.TASK_STATUS_IGNORED):
                ...  # Caller is blocked waiting for this code to run
                task_status.started()
                ...  # This async code can be interleaved with the caller

        :attr:`trio.TASK_STATUS_IGNORED` is a special global object with
        a do-nothing ``started`` method. This way your function supports
        being called either like ``await nursery.start(async_fn, arg1,
        arg2)`` or directly like ``await async_fn(arg1, arg2)``, and
        either way it can call :meth:`task_status.started() <TaskStatus.started>`
        without worrying about which mode it's in. Defining your function like
        this will make it obvious to readers that it supports being used
        in both modes.

        Before the child calls :meth:`task_status.started() <TaskStatus.started>`,
        it's effectively run underneath the call to :meth:`start`: if it
        raises an exception then that exception is reported by
        :meth:`start`, and does *not* propagate out of the nursery. If
        :meth:`start` is cancelled, then the child task is also
        cancelled.

        When the child calls :meth:`task_status.started() <TaskStatus.started>`,
        it's moved out from underneath :meth:`start` and into the given nursery.

        If the child task passes a value to :meth:`task_status.started(value) <TaskStatus.started>`,
        then :meth:`start` returns this value. Otherwise, it returns ``None``.
        """
        if self._closed:
            raise RuntimeError("Nursery is closed to new arrivals")
        try:
            self._pending_starts += 1
            # wrap internal nursery in try-except to unroll any exceptiongroups
            # to avoid wrapping pre-started() exceptions in an extra ExceptionGroup.
            # See #2611.
            try:
                # set strict_exception_groups = True to make sure we always unwrap
                # *this* nursery's exceptiongroup
                async with open_nursery(strict_exception_groups=True) as old_nursery:
                    task_status: _TaskStatus[Any] = _TaskStatus(old_nursery, self)
                    thunk = functools.partial(async_fn, task_status=task_status)
                    task = GLOBAL_RUN_CONTEXT.runner.spawn_impl(
                        thunk, args, old_nursery, name
                    )
                    task._eventual_parent_nursery = self
                    # Wait for either TaskStatus.started or an exception to
                    # cancel this nursery:
            except BaseExceptionGroup as exc:
                if len(exc.exceptions) == 1:
                    raise exc.exceptions[0] from None
                raise TrioInternalError(
                    "Internal nursery should not have multiple tasks. This can be "
                    'caused by the user managing to access the "old" nursery in '
                    "`task_status` and spawning tasks in it."
                ) from exc

            # If we get here, then the child either got reparented or exited
            # normally. The complicated logic is all in TaskStatus.started().
            # (Any exceptions propagate directly out of the above.)
            if task_status._value is _NoStatus:
                raise RuntimeError("child exited without calling task_status.started()")
            return task_status._value
        finally:
            self._pending_starts -= 1
            self._check_nursery_closed()

    def __del__(self) -> None:
        assert not self._children


################################################################
# Task and friends
################################################################


@final
@attrs.define(eq=False, hash=False, repr=False)
class Task(metaclass=NoPublicConstructor):
    _parent_nursery: Nursery | None
    coro: Coroutine[Any, Outcome[object], Any]
    _runner: Runner
    name: str
    context: contextvars.Context
    _counter: int = attrs.field(init=False, factory=itertools.count().__next__)

    # Invariant:
    # - for unscheduled tasks, _next_send_fn and _next_send are both None
    # - for scheduled tasks, _next_send_fn(_next_send) resumes the task;
    #   usually _next_send_fn is self.coro.send and _next_send is an
    #   Outcome. When recovering from a foreign await, _next_send_fn is
    #   self.coro.throw and _next_send is an exception. _next_send_fn
    #   will effectively be at the top of every task's call stack, so
    #   it should be written in C if you don't want to pollute Trio
    #   tracebacks with extraneous frames.
    # - for scheduled tasks, custom_sleep_data is None
    # Tasks start out unscheduled.
    _next_send_fn: Callable[[Any], object] | None = None
    _next_send: Outcome[Any] | None | BaseException = None
    _abort_func: Callable[[_core.RaiseCancelT], Abort] | None = None
    custom_sleep_data: Any = None

    # For introspection and nursery.start()
    _child_nurseries: list[Nursery] = attrs.Factory(list)
    _eventual_parent_nursery: Nursery | None = None

    # these are counts of how many cancel/schedule points this task has
    # executed, for assert{_no,}_checkpoints
    # XX maybe these should be exposed as part of a statistics() method?
    _cancel_points: int = 0
    _schedule_points: int = 0

    def __repr__(self) -> str:
        return f"<Task {self.name!r} at {id(self):#x}>"

    @property
    def parent_nursery(self) -> Nursery | None:
        """The nursery this task is inside (or None if this is the "init"
        task).

        Example use case: drawing a visualization of the task tree in a
        debugger.

        """
        return self._parent_nursery

    @property
    def eventual_parent_nursery(self) -> Nursery | None:
        """The nursery this task will be inside after it calls
        ``task_status.started()``.

        If this task has already called ``started()``, or if it was not
        spawned using `nursery.start() <trio.Nursery.start>`, then
        its `eventual_parent_nursery` is ``None``.

        """
        return self._eventual_parent_nursery

    @property
    def child_nurseries(self) -> list[Nursery]:
        """The nurseries this task contains.

        This is a list, with outer nurseries before inner nurseries.

        """
        return list(self._child_nurseries)

    def iter_await_frames(self) -> Iterator[tuple[types.FrameType, int]]:
        """Iterates recursively over the coroutine-like objects this
        task is waiting on, yielding the frame and line number at each
        frame.

        This is similar to `traceback.walk_stack` in a synchronous
        context. Note that `traceback.walk_stack` returns frames from
        the bottom of the call stack to the top, while this function
        starts from `Task.coro <trio.lowlevel.Task.coro>` and works it
        way down.

        Example usage: extracting a stack trace::

            import traceback

            def print_stack_for_task(task):
                ss = traceback.StackSummary.extract(task.iter_await_frames())
                print("".join(ss.format()))

        """
        # Ignore static typing as we're doing lots of dynamic introspection
        coro: Any = self.coro
        while coro is not None:
            if hasattr(coro, "cr_frame"):
                # A real coroutine
                yield coro.cr_frame, coro.cr_frame.f_lineno
                coro = coro.cr_await
            elif hasattr(coro, "gi_frame"):
                # A generator decorated with @types.coroutine
                yield coro.gi_frame, coro.gi_frame.f_lineno
                coro = coro.gi_yieldfrom
            elif coro.__class__.__name__ in [
                "async_generator_athrow",
                "async_generator_asend",
            ]:
                # cannot extract the generator directly, see https://github.com/python/cpython/issues/76991
                # we can however use the gc to look through the object
                for referent in gc.get_referents(coro):
                    if hasattr(referent, "ag_frame"):  # pragma: no branch
                        yield referent.ag_frame, referent.ag_frame.f_lineno
                        coro = referent.ag_await
                        break
                else:  # pragma: no cover
                    # either cpython changed or we are running on an alternative python implementation
                    return
            else:  # pragma: no cover
                return

    ################
    # Cancellation
    ################

    # The CancelStatus object that is currently active for this task.
    # Don't change this directly; instead, use _activate_cancel_status().
    # This can be None, but only in the init task.
    _cancel_status: CancelStatus = attrs.field(default=None, repr=False)

    def _activate_cancel_status(self, cancel_status: CancelStatus | None) -> None:
        if self._cancel_status is not None:
            self._cancel_status._tasks.remove(self)
        self._cancel_status = cancel_status  # type: ignore[assignment]
        if self._cancel_status is not None:
            self._cancel_status._tasks.add(self)
            if self._cancel_status.effectively_cancelled:
                self._attempt_delivery_of_any_pending_cancel()

    def _attempt_abort(self, raise_cancel: _core.RaiseCancelT) -> None:
        # Either the abort succeeds, in which case we will reschedule the
        # task, or else it fails, in which case it will worry about
        # rescheduling itself (hopefully eventually calling reraise to raise
        # the given exception, but not necessarily).

        # This is only called by the functions immediately below, which both check
        # `self.abort_func is not None`.
        assert self._abort_func is not None, "FATAL INTERNAL ERROR"

        success = self._abort_func(raise_cancel)
        if type(success) is not Abort:
            raise TrioInternalError("abort function must return Abort enum")
        # We only attempt to abort once per blocking call, regardless of
        # whether we succeeded or failed.
        self._abort_func = None
        if success is Abort.SUCCEEDED:
            self._runner.reschedule(self, capture(raise_cancel))

    def _attempt_delivery_of_any_pending_cancel(self) -> None:
        if self._abort_func is None:
            return
        if not self._cancel_status.effectively_cancelled:
            return

        def raise_cancel() -> NoReturn:
            raise Cancelled._create()

        self._attempt_abort(raise_cancel)

    def _attempt_delivery_of_pending_ki(self) -> None:
        assert self._runner.ki_pending
        if self._abort_func is None:
            return

        def raise_cancel() -> NoReturn:
            self._runner.ki_pending = False
            raise KeyboardInterrupt

        self._attempt_abort(raise_cancel)


################################################################
# The central Runner object
################################################################


class RunContext(threading.local):
    runner: Runner
    task: Task


GLOBAL_RUN_CONTEXT: Final = RunContext()


@attrs.frozen
class RunStatistics:
    """An object containing run-loop-level debugging information.

    Currently, the following fields are defined:

    * ``tasks_living`` (int): The number of tasks that have been spawned
      and not yet exited.
    * ``tasks_runnable`` (int): The number of tasks that are currently
      queued on the run queue (as opposed to blocked waiting for something
      to happen).
    * ``seconds_to_next_deadline`` (float): The time until the next
      pending cancel scope deadline. May be negative if the deadline has
      expired but we haven't yet processed cancellations. May be
      :data:`~math.inf` if there are no pending deadlines.
    * ``run_sync_soon_queue_size`` (int): The number of
      unprocessed callbacks queued via
      :meth:`trio.lowlevel.TrioToken.run_sync_soon`.
    * ``io_statistics`` (object): Some statistics from Trio's I/O
      backend. This always has an attribute ``backend`` which is a string
      naming which operating-system-specific I/O backend is in use; the
      other attributes vary between backends.
    """

    tasks_living: int
    tasks_runnable: int
    seconds_to_next_deadline: float
    io_statistics: IOStatistics
    run_sync_soon_queue_size: int


# This holds all the state that gets trampolined back and forth between
# callbacks when we're running in guest mode.
#
# It has to be a separate object from Runner, and Runner *cannot* hold
# references to it (directly or indirectly)!
#
# The idea is that we want a chance to detect if our host loop quits and stops
# driving us forward. We detect that by unrolled_run_gen being garbage
# collected, and hitting its 'except GeneratorExit:' block. So this only
# happens if unrolled_run_gen is GCed.
#
# The Runner state is referenced from the global GLOBAL_RUN_CONTEXT. The only
# way it gets *un*referenced is by unrolled_run_gen completing, e.g. by being
# GCed. But if Runner has a direct or indirect reference to it, and the host
# loop has abandoned it, then this will never happen!
#
# So this object can reference Runner, but Runner can't reference it. The only
# references to it are the "in flight" callback chain on the host loop /
# worker thread.


@attrs.define(eq=False, hash=False)
class GuestState:
    runner: Runner
    run_sync_soon_threadsafe: Callable[[Callable[[], object]], object]
    run_sync_soon_not_threadsafe: Callable[[Callable[[], object]], object]
    done_callback: Callable[[Outcome[Any]], object]
    unrolled_run_gen: Generator[float, EventResult, None]
    unrolled_run_next_send: Outcome[Any] = attrs.Factory(lambda: Value(None))

    def guest_tick(self) -> None:
        prev_library, sniffio_library.name = sniffio_library.name, "trio"
        try:
            timeout = self.unrolled_run_next_send.send(self.unrolled_run_gen)
        except StopIteration:
            assert self.runner.main_task_outcome is not None
            self.done_callback(self.runner.main_task_outcome)
            return
        except TrioInternalError as exc:
            self.done_callback(Error(exc))
            return
        finally:
            sniffio_library.name = prev_library

        # Optimization: try to skip going into the thread if we can avoid it
        events_outcome: Value[EventResult] | Error = capture(
            self.runner.io_manager.get_events, 0
        )
        if timeout <= 0 or isinstance(events_outcome, Error) or events_outcome.value:
            # No need to go into the thread
            self.unrolled_run_next_send = events_outcome
            self.runner.guest_tick_scheduled = True
            self.run_sync_soon_not_threadsafe(self.guest_tick)
        else:
            # Need to go into the thread and call get_events() there
            self.runner.guest_tick_scheduled = False

            def get_events() -> EventResult:
                return self.runner.io_manager.get_events(timeout)

            def deliver(events_outcome: Outcome[EventResult]) -> None:
                def in_main_thread() -> None:
                    self.unrolled_run_next_send = events_outcome
                    self.runner.guest_tick_scheduled = True
                    self.guest_tick()

                self.run_sync_soon_threadsafe(in_main_thread)

            start_thread_soon(get_events, deliver)


@attrs.define(eq=False, hash=False)
class Runner:
    clock: Clock
    instruments: Instruments
    io_manager: TheIOManager
    ki_manager: KIManager
    strict_exception_groups: bool

    # Run-local values, see _local.py
    _locals: dict[_core.RunVar[Any], Any] = attrs.Factory(dict)

    runq: deque[Task] = attrs.Factory(deque)
    tasks: set[Task] = attrs.Factory(set)

    deadlines: Deadlines = attrs.Factory(Deadlines)

    init_task: Task | None = None
    system_nursery: Nursery | None = None
    system_context: contextvars.Context = attrs.field(kw_only=True)
    main_task: Task | None = None
    main_task_outcome: Outcome[Any] | None = None

    entry_queue: EntryQueue = attrs.Factory(EntryQueue)
    trio_token: TrioToken | None = None
    asyncgens: AsyncGenerators = attrs.Factory(AsyncGenerators)

    # If everything goes idle for this long, we call clock._autojump()
    clock_autojump_threshold: float = inf

    # Guest mode stuff
    is_guest: bool = False
    guest_tick_scheduled: bool = False

    def force_guest_tick_asap(self) -> None:
        if self.guest_tick_scheduled:
            return
        self.guest_tick_scheduled = True
        self.io_manager.force_wakeup()

    def close(self) -> None:
        self.io_manager.close()
        self.entry_queue.close()
        self.asyncgens.close()
        if "after_run" in self.instruments:
            self.instruments.call("after_run")
        # This is where KI protection gets disabled, so we do it last
        self.ki_manager.close()

    @_public
    def current_statistics(self) -> RunStatistics:
        """Returns ``RunStatistics``, which contains run-loop-level debugging information.

        Currently, the following fields are defined:

        * ``tasks_living`` (int): The number of tasks that have been spawned
          and not yet exited.
        * ``tasks_runnable`` (int): The number of tasks that are currently
          queued on the run queue (as opposed to blocked waiting for something
          to happen).
        * ``seconds_to_next_deadline`` (float): The time until the next
          pending cancel scope deadline. May be negative if the deadline has
          expired but we haven't yet processed cancellations. May be
          :data:`~math.inf` if there are no pending deadlines.
        * ``run_sync_soon_queue_size`` (int): The number of
          unprocessed callbacks queued via
          :meth:`trio.lowlevel.TrioToken.run_sync_soon`.
        * ``io_statistics`` (object): Some statistics from Trio's I/O
          backend. This always has an attribute ``backend`` which is a string
          naming which operating-system-specific I/O backend is in use; the
          other attributes vary between backends.

        """
        seconds_to_next_deadline = self.deadlines.next_deadline() - self.current_time()
        return RunStatistics(
            tasks_living=len(self.tasks),
            tasks_runnable=len(self.runq),
            seconds_to_next_deadline=seconds_to_next_deadline,
            io_statistics=self.io_manager.statistics(),
            run_sync_soon_queue_size=self.entry_queue.size(),
        )

    @_public
    def current_time(self) -> float:
        """Returns the current time according to Trio's internal clock.

        Returns:
            float: The current time.

        Raises:
            RuntimeError: if not inside a call to :func:`trio.run`.

        """
        return self.clock.current_time()

    @_public
    def current_clock(self) -> Clock:
        """Returns the current :class:`~trio.abc.Clock`."""
        return self.clock

    @_public
    def current_root_task(self) -> Task | None:
        """Returns the current root :class:`Task`.

        This is the task that is the ultimate parent of all other tasks.

        """
        return self.init_task

    ################
    # Core task handling primitives
    ################

    @_public  # Type-ignore due to use of Any here.
    def reschedule(  # type: ignore[misc]
        self, task: Task, next_send: Outcome[Any] = _NO_SEND
    ) -> None:
        """Reschedule the given task with the given
        :class:`outcome.Outcome`.

        See :func:`wait_task_rescheduled` for the gory details.

        There must be exactly one call to :func:`reschedule` for every call to
        :func:`wait_task_rescheduled`. (And when counting, keep in mind that
        returning :data:`Abort.SUCCEEDED` from an abort callback is equivalent
        to calling :func:`reschedule` once.)

        Args:
          task (trio.lowlevel.Task): the task to be rescheduled. Must be blocked
              in a call to :func:`wait_task_rescheduled`.
          next_send (outcome.Outcome): the value (or error) to return (or
              raise) from :func:`wait_task_rescheduled`.

        """
        if next_send is _NO_SEND:
            next_send = Value(None)

        assert task._runner is self
        assert task._next_send_fn is None
        task._next_send_fn = task.coro.send
        task._next_send = next_send
        task._abort_func = None
        task.custom_sleep_data = None
        if not self.runq and self.is_guest:
            self.force_guest_tick_asap()
        self.runq.append(task)
        if "task_scheduled" in self.instruments:
            self.instruments.call("task_scheduled", task)

    def spawn_impl(
        self,
        async_fn: Callable[[Unpack[PosArgT]], Awaitable[object]],
        args: tuple[Unpack[PosArgT]],
        nursery: Nursery | None,
        name: object,
        *,
        system_task: bool = False,
        context: contextvars.Context | None = None,
    ) -> Task:
        ######
        # Make sure the nursery is in working order
        ######

        # This sorta feels like it should be a method on nursery, except it
        # has to handle nursery=None for init. And it touches the internals of
        # all kinds of objects.
        if nursery is not None and nursery._closed:
            raise RuntimeError("Nursery is closed to new arrivals")
        if nursery is None:
            assert self.init_task is None

        ######
        # Propagate contextvars
        ######
        if context is None:
            context = self.system_context.copy() if system_task else copy_context()

        ######
        # Call the function and get the coroutine object, while giving helpful
        # errors for common mistakes.
        ######
        # TypeVarTuple passed into ParamSpec function confuses Mypy.
        coro = context.run(coroutine_or_error, async_fn, *args)  # type: ignore[arg-type]

        if name is None:
            name = async_fn
        if isinstance(name, functools.partial):
            name = name.func
        if not isinstance(name, str):
            try:
                name = f"{name.__module__}.{name.__qualname__}"  # type: ignore[attr-defined]
            except AttributeError:
                name = repr(name)

        # very old Cython versions (<0.29.24) has the attribute, but with a value of None
        if getattr(coro, "cr_frame", None) is None:
            # This async function is implemented in C or Cython
            async def python_wrapper(orig_coro: Awaitable[RetT]) -> RetT:
                return await orig_coro

            coro = python_wrapper(coro)
        coro.cr_frame.f_locals.setdefault(LOCALS_KEY_KI_PROTECTION_ENABLED, system_task)

        ######
        # Set up the Task object
        ######
        task = Task._create(
            coro=coro, parent_nursery=nursery, runner=self, name=name, context=context
        )

        self.tasks.add(task)
        if nursery is not None:
            nursery._children.add(task)
            task._activate_cancel_status(nursery._cancel_status)

        if "task_spawned" in self.instruments:
            self.instruments.call("task_spawned", task)
        # Special case: normally next_send should be an Outcome, but for the
        # very first send we have to send a literal unboxed None.
        self.reschedule(task, None)  # type: ignore[arg-type]
        return task

    def task_exited(self, task: Task, outcome: Outcome[Any]) -> None:
        if (
            task._cancel_status is not None
            and task._cancel_status.abandoned_by_misnesting
            and task._cancel_status.parent is None
        ):
            # The cancel scope surrounding this task's nursery was closed
            # before the task exited. Force the task to exit with an error,
            # since the error might not have been caught elsewhere. See the
            # comments in CancelStatus.close().
            try:
                # Raise this, rather than just constructing it, to get a
                # traceback frame included
                raise RuntimeError(
                    "Cancel scope stack corrupted: cancel scope surrounding "
                    f"{task!r} was closed before the task exited\n{MISNESTING_ADVICE}"
                )
            except RuntimeError as new_exc:
                if isinstance(outcome, Error):
                    new_exc.__context__ = outcome.error
                outcome = Error(new_exc)

        task._activate_cancel_status(None)
        self.tasks.remove(task)
        if task is self.init_task:
            # If the init task crashed, then something is very wrong and we
            # let the error propagate. (It'll eventually be wrapped in a
            # TrioInternalError.)
            outcome.unwrap()
            # the init task should be the last task to exit. If not, then
            # something is very wrong.
            if self.tasks:  # pragma: no cover
                raise TrioInternalError
        else:
            if task is self.main_task:
                self.main_task_outcome = outcome
                outcome = Value(None)
            assert task._parent_nursery is not None, task
            task._parent_nursery._child_finished(task, outcome)

        if "task_exited" in self.instruments:
            self.instruments.call("task_exited", task)

    ################
    # System tasks and init
    ################

    @_public
    def spawn_system_task(
        self,
        async_fn: Callable[[Unpack[PosArgT]], Awaitable[object]],
        *args: Unpack[PosArgT],
        name: object = None,
        context: contextvars.Context | None = None,
    ) -> Task:
        """Spawn a "system" task.

        System tasks have a few differences from regular tasks:

        * They don't need an explicit nursery; instead they go into the
          internal "system nursery".

        * If a system task raises an exception, then it's converted into a
          :exc:`~trio.TrioInternalError` and *all* tasks are cancelled. If you
          write a system task, you should be careful to make sure it doesn't
          crash.

        * System tasks are automatically cancelled when the main task exits.

        * By default, system tasks have :exc:`KeyboardInterrupt` protection
          *enabled*. If you want your task to be interruptible by control-C,
          then you need to use :func:`disable_ki_protection` explicitly (and
          come up with some plan for what to do with a
          :exc:`KeyboardInterrupt`, given that system tasks aren't allowed to
          raise exceptions).

        * System tasks do not inherit context variables from their creator.

        Towards the end of a call to :meth:`trio.run`, after the main
        task and all system tasks have exited, the system nursery
        becomes closed. At this point, new calls to
        :func:`spawn_system_task` will raise ``RuntimeError("Nursery
        is closed to new arrivals")`` instead of creating a system
        task. It's possible to encounter this state either in
        a ``finally`` block in an async generator, or in a callback
        passed to :meth:`TrioToken.run_sync_soon` at the right moment.

        Args:
          async_fn: An async callable.
          args: Positional arguments for ``async_fn``. If you want to pass
              keyword arguments, use :func:`functools.partial`.
          name: The name for this task. Only used for debugging/introspection
              (e.g. ``repr(task_obj)``). If this isn't a string,
              :func:`spawn_system_task` will try to make it one. A common use
              case is if you're wrapping a function before spawning a new
              task, you might pass the original function as the ``name=`` to
              make debugging easier.
          context: An optional ``contextvars.Context`` object with context variables
              to use for this task. You would normally get a copy of the current
              context with ``context = contextvars.copy_context()`` and then you would
              pass that ``context`` object here.

        Returns:
          Task: the newly spawned task

        """
        return self.spawn_impl(
            async_fn,
            args,
            self.system_nursery,
            name,
            system_task=True,
            context=context,
        )

    async def init(
        self,
        async_fn: Callable[[Unpack[PosArgT]], Awaitable[object]],
        args: tuple[Unpack[PosArgT]],
    ) -> None:
        # run_sync_soon task runs here:
        async with open_nursery() as run_sync_soon_nursery:
            # All other system tasks run here:
            async with open_nursery() as self.system_nursery:
                # Only the main task runs here:
                async with open_nursery() as main_task_nursery:
                    try:
                        self.main_task = self.spawn_impl(
                            async_fn, args, main_task_nursery, None
                        )
                    except BaseException as exc:
                        self.main_task_outcome = Error(exc)
                        return
                    self.spawn_impl(
                        self.entry_queue.task,
                        (),
                        run_sync_soon_nursery,
                        "<TrioToken.run_sync_soon task>",
                        system_task=True,
                    )

                # Main task is done; start shutting down system tasks
                self.system_nursery.cancel_scope.cancel()

            # System nursery is closed; finalize remaining async generators
            await self.asyncgens.finalize_remaining(self)

            # There are no more asyncgens, which means no more user-provided
            # code except possibly run_sync_soon callbacks. It's finally safe
            # to stop the run_sync_soon task and exit run().
            run_sync_soon_nursery.cancel_scope.cancel()

    ################
    # Outside context problems
    ################

    @_public
    def current_trio_token(self) -> TrioToken:
        """Retrieve the :class:`TrioToken` for the current call to
        :func:`trio.run`.

        """
        if self.trio_token is None:
            self.trio_token = TrioToken._create(self.entry_queue)
        return self.trio_token

    ################
    # KI handling
    ################

    ki_pending: bool = False

    # deliver_ki is broke. Maybe move all the actual logic and state into
    # RunToken, and we'll only have one instance per runner? But then we can't
    # have a public constructor. Eh, but current_run_token() returning a
    # unique object per run feels pretty nice. Maybe let's just go for it. And
    # keep the class public so people can isinstance() it if they want.

    # This gets called from signal context
    def deliver_ki(self) -> None:
        self.ki_pending = True
        with suppress(RunFinishedError):
            self.entry_queue.run_sync_soon(self._deliver_ki_cb)

    def _deliver_ki_cb(self) -> None:
        if not self.ki_pending:
            return
        # Can't happen because main_task and run_sync_soon_task are created at
        # the same time -- so even if KI arrives before main_task is created,
        # we won't get here until afterwards.
        assert self.main_task is not None
        if self.main_task_outcome is not None:
            # We're already in the process of exiting -- leave ki_pending set
            # and we'll check it again on our way out of run().
            return
        self.main_task._attempt_delivery_of_pending_ki()

    ################
    # Quiescing
    ################

    # sortedcontainers doesn't have types, and is reportedly very hard to type:
    # https://github.com/grantjenks/python-sortedcontainers/issues/68
    waiting_for_idle: Any = attrs.Factory(SortedDict)

    @_public
    async def wait_all_tasks_blocked(self, cushion: float = 0.0) -> None:
        """Block until there are no runnable tasks.

        This is useful in testing code when you want to give other tasks a
        chance to "settle down". The calling task is blocked, and doesn't wake
        up until all other tasks are also blocked for at least ``cushion``
        seconds. (Setting a non-zero ``cushion`` is intended to handle cases
        like two tasks talking to each other over a local socket, where we
        want to ignore the potential brief moment between a send and receive
        when all tasks are blocked.)

        Note that ``cushion`` is measured in *real* time, not the Trio clock
        time.

        If there are multiple tasks blocked in :func:`wait_all_tasks_blocked`,
        then the one with the shortest ``cushion`` is the one woken (and
        this task becoming unblocked resets the timers for the remaining
        tasks). If there are multiple tasks that have exactly the same
        ``cushion``, then all are woken.

        You should also consider :class:`trio.testing.Sequencer`, which
        provides a more explicit way to control execution ordering within a
        test, and will often produce more readable tests.

        Example:
          Here's an example of one way to test that Trio's locks are fair: we
          take the lock in the parent, start a child, wait for the child to be
          blocked waiting for the lock (!), and then check that we can't
          release and immediately re-acquire the lock::

             async def lock_taker(lock):
                 await lock.acquire()
                 lock.release()

             async def test_lock_fairness():
                 lock = trio.Lock()
                 await lock.acquire()
                 async with trio.open_nursery() as nursery:
                     nursery.start_soon(lock_taker, lock)
                     # child hasn't run yet, we have the lock
                     assert lock.locked()
                     assert lock._owner is trio.lowlevel.current_task()
                     await trio.testing.wait_all_tasks_blocked()
                     # now the child has run and is blocked on lock.acquire(), we
                     # still have the lock
                     assert lock.locked()
                     assert lock._owner is trio.lowlevel.current_task()
                     lock.release()
                     try:
                         # The child has a prior claim, so we can't have it
                         lock.acquire_nowait()
                     except trio.WouldBlock:
                         assert lock._owner is not trio.lowlevel.current_task()
                         print("PASS")
                     else:
                         print("FAIL")

        """
        task = current_task()
        key = (cushion, id(task))
        self.waiting_for_idle[key] = task

        def abort(_: _core.RaiseCancelT) -> Abort:
            del self.waiting_for_idle[key]
            return Abort.SUCCEEDED

        await wait_task_rescheduled(abort)


################################################################
# run
################################################################
#
# Trio's core task scheduler and coroutine runner is in 'unrolled_run'. It's
# called that because it has an unusual feature: it's actually a generator.
# Whenever it needs to fetch IO events from the OS, it yields, and waits for
# its caller to send the IO events back in. So the loop is "unrolled" into a
# sequence of generator send() calls.
#
# The reason for this unusual design is to support two different modes of
# operation, where the IO is handled differently.
#
# In normal mode using trio.run, the scheduler and IO run in the same thread:
#
# Main thread:
#
# +---------------------------+
# | Run tasks                 |
# | (unrolled_run)            |
# +---------------------------+
# | Block waiting for I/O     |
# | (io_manager.get_events)   |
# +---------------------------+
# | Run tasks                 |
# | (unrolled_run)            |
# +---------------------------+
# | Block waiting for I/O     |
# | (io_manager.get_events)   |
# +---------------------------+
# :
#
#
# In guest mode using trio.lowlevel.start_guest_run, the scheduler runs on the
# main thread as a host loop callback, but blocking for IO gets pushed into a
# worker thread:
#
# Main thread executing host loop:           Trio I/O thread:
#
# +---------------------------+
# | Run Trio tasks            |
# | (unrolled_run)            |
# +---------------------------+ --------------+
#                                             v
# +---------------------------+              +----------------------------+
# | Host loop does whatever   |              | Block waiting for Trio I/O |
# | it wants                  |              | (io_manager.get_events)    |
# +---------------------------+              +----------------------------+
#                                             |
# +---------------------------+ <-------------+
# | Run Trio tasks            |
# | (unrolled_run)            |
# +---------------------------+ --------------+
#                                             v
# +---------------------------+              +----------------------------+
# | Host loop does whatever   |              | Block waiting for Trio I/O |
# | it wants                  |              | (io_manager.get_events)    |
# +---------------------------+              +----------------------------+
# :                                            :
#
# Most of Trio's internals don't need to care about this difference. The main
# complication it creates is that in guest mode, we might need to wake up not
# just due to OS-reported IO events, but also because of code running on the
# host loop calling reschedule() or changing task deadlines. Search for
# 'is_guest' to see the special cases we need to handle this.


def setup_runner(
    clock: Clock | None,
    instruments: Sequence[Instrument],
    restrict_keyboard_interrupt_to_checkpoints: bool,
    strict_exception_groups: bool,
) -> Runner:
    """Create a Runner object and install it as the GLOBAL_RUN_CONTEXT."""
    # It wouldn't be *hard* to support nested calls to run(), but I can't
    # think of a single good reason for it, so let's be conservative for
    # now:
    if hasattr(GLOBAL_RUN_CONTEXT, "runner"):
        raise RuntimeError("Attempted to call run() from inside a run()")

    if clock is None:
        clock = SystemClock()
    instrument_group = Instruments(instruments)
    io_manager = TheIOManager()
    system_context = copy_context()
    ki_manager = KIManager()

    runner = Runner(
        clock=clock,
        instruments=instrument_group,
        io_manager=io_manager,
        system_context=system_context,
        ki_manager=ki_manager,
        strict_exception_groups=strict_exception_groups,
    )
    runner.asyncgens.install_hooks(runner)

    # This is where KI protection gets enabled, so we want to do it early - in
    # particular before we start modifying global state like GLOBAL_RUN_CONTEXT
    ki_manager.install(runner.deliver_ki, restrict_keyboard_interrupt_to_checkpoints)

    GLOBAL_RUN_CONTEXT.runner = runner
    return runner


def run(
    async_fn: Callable[..., Awaitable[RetT]],
    *args: object,
    clock: Clock | None = None,
    instruments: Sequence[Instrument] = (),
    restrict_keyboard_interrupt_to_checkpoints: bool = False,
    strict_exception_groups: bool = True,
) -> RetT:
    """Run a Trio-flavored async function, and return the result.

    Calling::

       run(async_fn, *args)

    is the equivalent of::

       await async_fn(*args)

    except that :func:`run` can (and must) be called from a synchronous
    context.

    This is Trio's main entry point. Almost every other function in Trio
    requires that you be inside a call to :func:`run`.

    Args:
      async_fn: An async function.

      args: Positional arguments to be passed to *async_fn*. If you need to
          pass keyword arguments, then use :func:`functools.partial`.

      clock: ``None`` to use the default system-specific monotonic clock;
          otherwise, an object implementing the :class:`trio.abc.Clock`
          interface, like (for example) a :class:`trio.testing.MockClock`
          instance.

      instruments (list of :class:`trio.abc.Instrument` objects): Any
          instrumentation you want to apply to this run. This can also be
          modified during the run; see :ref:`instrumentation`.

      restrict_keyboard_interrupt_to_checkpoints (bool): What happens if the
          user hits control-C while :func:`run` is running? If this argument
          is False (the default), then you get the standard Python behavior: a
          :exc:`KeyboardInterrupt` exception will immediately interrupt
          whatever task is running (or if no task is running, then Trio will
          wake up a task to be interrupted). Alternatively, if you set this
          argument to True, then :exc:`KeyboardInterrupt` delivery will be
          delayed: it will be *only* be raised at :ref:`checkpoints
          <checkpoints>`, like a :exc:`Cancelled` exception.

          The default behavior is nice because it means that even if you
          accidentally write an infinite loop that never executes any
          checkpoints, then you can still break out of it using control-C.
          The alternative behavior is nice if you're paranoid about a
          :exc:`KeyboardInterrupt` at just the wrong place leaving your
          program in an inconsistent state, because it means that you only
          have to worry about :exc:`KeyboardInterrupt` at the exact same
          places where you already have to worry about :exc:`Cancelled`.

          This setting has no effect if your program has registered a custom
          SIGINT handler, or if :func:`run` is called from anywhere but the
          main thread (this is a Python limitation), or if you use
          :func:`open_signal_receiver` to catch SIGINT.

      strict_exception_groups (bool): Unless set to False, nurseries will always wrap
          even a single raised exception in an exception group. This can be overridden
          on the level of individual nurseries. Setting it to False will be deprecated
          and ultimately removed in a future version of Trio.

    Returns:
      Whatever ``async_fn`` returns.

    Raises:
      TrioInternalError: if an unexpected error is encountered inside Trio's
          internal machinery. This is a bug and you should `let us know
          <https://github.com/python-trio/trio/issues>`__.

      Anything else: if ``async_fn`` raises an exception, then :func:`run`
          propagates it.

    """
    if strict_exception_groups is not None and not strict_exception_groups:
        warn_deprecated(
            "trio.run(..., strict_exception_groups=False)",
            version="0.24.1",
            issue=2929,
            instead="the default value of True and rewrite exception handlers to handle ExceptionGroups",
        )

    __tracebackhide__ = True

    runner = setup_runner(
        clock,
        instruments,
        restrict_keyboard_interrupt_to_checkpoints,
        strict_exception_groups,
    )

    prev_library, sniffio_library.name = sniffio_library.name, "trio"
    try:
        gen = unrolled_run(runner, async_fn, args)
        # Need to send None in the first time.
        next_send: EventResult = None  # type: ignore[assignment]
        while True:
            try:
                timeout = gen.send(next_send)
            except StopIteration:
                break
            next_send = runner.io_manager.get_events(timeout)
    finally:
        sniffio_library.name = prev_library
    # Inlined copy of runner.main_task_outcome.unwrap() to avoid
    # cluttering every single Trio traceback with an extra frame.
    if isinstance(runner.main_task_outcome, Value):
        return cast(RetT, runner.main_task_outcome.value)
    elif isinstance(runner.main_task_outcome, Error):
        raise runner.main_task_outcome.error
    else:  # pragma: no cover
        raise AssertionError(runner.main_task_outcome)


def start_guest_run(
    async_fn: Callable[..., Awaitable[RetT]],
    *args: object,
    run_sync_soon_threadsafe: Callable[[Callable[[], object]], object],
    done_callback: Callable[[outcome.Outcome[RetT]], object],
    run_sync_soon_not_threadsafe: (
        Callable[[Callable[[], object]], object] | None
    ) = None,
    host_uses_signal_set_wakeup_fd: bool = False,
    clock: Clock | None = None,
    instruments: Sequence[Instrument] = (),
    restrict_keyboard_interrupt_to_checkpoints: bool = False,
    strict_exception_groups: bool = True,
) -> None:
    """Start a "guest" run of Trio on top of some other "host" event loop.

    Each host loop can only have one guest run at a time.

    You should always let the Trio run finish before stopping the host loop;
    if not, it may leave Trio's internal data structures in an inconsistent
    state. You might be able to get away with it if you immediately exit the
    program, but it's safest not to go there in the first place.

    Generally, the best way to do this is wrap this in a function that starts
    the host loop and then immediately starts the guest run, and then shuts
    down the host when the guest run completes.

    Once :func:`start_guest_run` returns successfully, the guest run
    has been set up enough that you can invoke sync-colored Trio
    functions such as :func:`~trio.current_time`, :func:`spawn_system_task`,
    and :func:`current_trio_token`. If a `~trio.TrioInternalError` occurs
    during this early setup of the guest run, it will be raised out of
    :func:`start_guest_run`.  All other errors, including all errors
    raised by the *async_fn*, will be delivered to your
    *done_callback* at some point after :func:`start_guest_run` returns
    successfully.

    Args:

      run_sync_soon_threadsafe: An arbitrary callable, which will be passed a
         function as its sole argument::

            def my_run_sync_soon_threadsafe(fn):
                ...

         This callable should schedule ``fn()`` to be run by the host on its
         next pass through its loop. **Must support being called from
         arbitrary threads.**

      done_callback: An arbitrary callable::

            def my_done_callback(run_outcome):
                ...

         When the Trio run has finished, Trio will invoke this callback to let
         you know. The argument is an `outcome.Outcome`, reporting what would
         have been returned or raised by `trio.run`. This function can do
         anything you want, but commonly you'll want it to shut down the
         host loop, unwrap the outcome, etc.

      run_sync_soon_not_threadsafe: Like ``run_sync_soon_threadsafe``, but
         will only be called from inside the host loop's main thread.
         Optional, but if your host loop allows you to implement this more
         efficiently than ``run_sync_soon_threadsafe`` then passing it will
         make things a bit faster.

      host_uses_signal_set_wakeup_fd (bool): Pass `True` if your host loop
         uses `signal.set_wakeup_fd`, and `False` otherwise. For more details,
         see :ref:`guest-run-implementation`.

    For the meaning of other arguments, see `trio.run`.

    """
    if strict_exception_groups is not None and not strict_exception_groups:
        warn_deprecated(
            "trio.start_guest_run(..., strict_exception_groups=False)",
            version="0.24.1",
            issue=2929,
            instead="the default value of True and rewrite exception handlers to handle ExceptionGroups",
        )

    runner = setup_runner(
        clock,
        instruments,
        restrict_keyboard_interrupt_to_checkpoints,
        strict_exception_groups,
    )
    runner.is_guest = True
    runner.guest_tick_scheduled = True

    if run_sync_soon_not_threadsafe is None:
        run_sync_soon_not_threadsafe = run_sync_soon_threadsafe

    guest_state = GuestState(
        runner=runner,
        run_sync_soon_threadsafe=run_sync_soon_threadsafe,
        run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
        done_callback=done_callback,
        unrolled_run_gen=unrolled_run(
            runner,
            async_fn,
            args,
            host_uses_signal_set_wakeup_fd=host_uses_signal_set_wakeup_fd,
        ),
    )

    # Run a few ticks of the guest run synchronously, so that by the
    # time we return, the system nursery exists and callers can use
    # spawn_system_task. We don't actually run any user code during
    # this time, so it shouldn't be possible to get an exception here,
    # except for a TrioInternalError.
    next_send = cast(
        EventResult, None
    )  # First iteration must be `None`, every iteration after that is EventResult
    for _tick in range(5):  # expected need is 2 iterations + leave some wiggle room
        if runner.system_nursery is not None:
            # We're initialized enough to switch to async guest ticks
            break
        try:
            timeout = guest_state.unrolled_run_gen.send(next_send)
        except StopIteration:  # pragma: no cover
            raise TrioInternalError(
                "Guest runner exited before system nursery was initialized"
            ) from None
        if timeout != 0:  # pragma: no cover
            guest_state.unrolled_run_gen.throw(
                TrioInternalError(
                    "Guest runner blocked before system nursery was initialized"
                )
            )
        # next_send should be the return value of
        # IOManager.get_events() if no I/O was waiting, which is
        # platform-dependent. We don't actually check for I/O during
        # this init phase because no one should be expecting any yet.
        if sys.platform == "win32":
            next_send = 0
        else:
            next_send = []
    else:  # pragma: no cover
        guest_state.unrolled_run_gen.throw(
            TrioInternalError(
                "Guest runner yielded too many times before "
                "system nursery was initialized"
            )
        )

    guest_state.unrolled_run_next_send = Value(next_send)
    run_sync_soon_not_threadsafe(guest_state.guest_tick)


# 24 hours is arbitrary, but it avoids issues like people setting timeouts of
# 10**20 and then getting integer overflows in the underlying system calls.
_MAX_TIMEOUT: Final = 24 * 60 * 60


# Weird quirk: this is written as a generator in order to support "guest
# mode", where our core event loop gets unrolled into a series of callbacks on
# the host loop. If you're doing a regular trio.run then this gets run
# straight through.
def unrolled_run(
    runner: Runner,
    async_fn: Callable[[Unpack[PosArgT]], Awaitable[object]],
    args: tuple[Unpack[PosArgT]],
    host_uses_signal_set_wakeup_fd: bool = False,
) -> Generator[float, EventResult, None]:
    locals()[LOCALS_KEY_KI_PROTECTION_ENABLED] = True
    __tracebackhide__ = True

    try:
        if not host_uses_signal_set_wakeup_fd:
            runner.entry_queue.wakeup.wakeup_on_signals()

        if "before_run" in runner.instruments:
            runner.instruments.call("before_run")
        runner.clock.start_clock()
        runner.init_task = runner.spawn_impl(
            runner.init, (async_fn, args), None, "<init>", system_task=True
        )

        # You know how people talk about "event loops"? This 'while' loop right
        # here is our event loop:
        while runner.tasks:
            if runner.runq:
                timeout: float = 0
            else:
                deadline = runner.deadlines.next_deadline()
                timeout = runner.clock.deadline_to_sleep_time(deadline)
            timeout = min(max(0, timeout), _MAX_TIMEOUT)

            idle_primed = None
            if runner.waiting_for_idle:
                cushion, _ = runner.waiting_for_idle.keys()[0]
                if cushion < timeout:
                    timeout = cushion
                    idle_primed = IdlePrimedTypes.WAITING_FOR_IDLE
            # We use 'elif' here because if there are tasks in
            # wait_all_tasks_blocked, then those tasks will wake up without
            # jumping the clock, so we don't need to autojump.
            elif runner.clock_autojump_threshold < timeout:
                timeout = runner.clock_autojump_threshold
                idle_primed = IdlePrimedTypes.AUTOJUMP_CLOCK

            if "before_io_wait" in runner.instruments:
                runner.instruments.call("before_io_wait", timeout)

            # Driver will call io_manager.get_events(timeout) and pass it back
            # in through the yield
            events = yield timeout
            runner.io_manager.process_events(events)

            if "after_io_wait" in runner.instruments:
                runner.instruments.call("after_io_wait", timeout)

            # Process cancellations due to deadline expiry
            now = runner.clock.current_time()
            if runner.deadlines.expire(now):
                idle_primed = None

            # idle_primed != None means: if the IO wait hit the timeout, and
            # still nothing is happening, then we should start waking up
            # wait_all_tasks_blocked tasks or autojump the clock. But there
            # are some subtleties in defining "nothing is happening".
            #
            # 'not runner.runq' means that no tasks are currently runnable.
            # 'not events' means that the last IO wait call hit its full
            # timeout. These are very similar, and if idle_primed != None and
            # we're running in regular mode then they always go together. But,
            # in *guest* mode, they can happen independently, even when
            # idle_primed=True:
            #
            # - runner.runq=empty and events=True: the host loop adjusted a
            #   deadline and that forced an IO wakeup before the timeout expired,
            #   even though no actual tasks were scheduled.
            #
            # - runner.runq=nonempty and events=False: the IO wait hit its
            #   timeout, but then some code in the host thread rescheduled a task
            #   before we got here.
            #
            # So we need to check both.
            if idle_primed is not None and not runner.runq and not events:
                if idle_primed is IdlePrimedTypes.WAITING_FOR_IDLE:
                    while runner.waiting_for_idle:
                        key, task = runner.waiting_for_idle.peekitem(0)
                        if key[0] == cushion:
                            del runner.waiting_for_idle[key]
                            runner.reschedule(task)
                        else:
                            break
                else:
                    assert idle_primed is IdlePrimedTypes.AUTOJUMP_CLOCK
                    assert isinstance(runner.clock, _core.MockClock)
                    runner.clock._autojump()

            # Process all runnable tasks, but only the ones that are already
            # runnable now. Anything that becomes runnable during this cycle
            # needs to wait until the next pass. This avoids various
            # starvation issues by ensuring that there's never an unbounded
            # delay between successive checks for I/O.
            #
            # Also, we randomize the order of each batch to avoid assumptions
            # about scheduling order sneaking in. In the long run, I suspect
            # we'll either (a) use strict FIFO ordering and document that for
            # predictability/determinism, or (b) implement a more
            # sophisticated scheduler (e.g. some variant of fair queueing),
            # for better behavior under load. For now, this is the worst of
            # both worlds - but it keeps our options open. (If we do decide to
            # go all in on deterministic scheduling, then there are other
            # things that will probably need to change too, like the deadlines
            # tie-breaker and the non-deterministic ordering of
            # task._notify_queues.)
            batch = list(runner.runq)
            runner.runq.clear()
            if _ALLOW_DETERMINISTIC_SCHEDULING:
                # We're running under Hypothesis, and pytest-trio has patched
                # this in to make the scheduler deterministic and avoid flaky
                # tests. It's not worth the (small) performance cost in normal
                # operation, since we'll shuffle the list and _r is only
                # seeded for tests.
                batch.sort(key=lambda t: t._counter)
                _r.shuffle(batch)
            else:
                # 50% chance of reversing the batch, this way each task
                # can appear before/after any other task.
                if _r.random() < 0.5:
                    batch.reverse()
            while batch:
                task = batch.pop()
                GLOBAL_RUN_CONTEXT.task = task

                if "before_task_step" in runner.instruments:
                    runner.instruments.call("before_task_step", task)

                next_send_fn = task._next_send_fn
                next_send = task._next_send
                task._next_send_fn = task._next_send = None
                final_outcome: Outcome[Any] | None = None
                try:
                    # We used to unwrap the Outcome object here and send/throw
                    # its contents in directly, but it turns out that .throw()
                    # is buggy on CPython (all versions at time of writing):
                    #   https://bugs.python.org/issue29587
                    #   https://bugs.python.org/issue29590
                    #   https://bugs.python.org/issue40694
                    #   https://github.com/python/cpython/issues/108668
                    # So now we send in the Outcome object and unwrap it on the
                    # other side.
                    msg = task.context.run(next_send_fn, next_send)
                except StopIteration as stop_iteration:
                    final_outcome = Value(stop_iteration.value)
                except BaseException as task_exc:
                    # Store for later, removing uninteresting top frames: 1
                    # frame we always remove, because it's this function
                    # catching it, and then in addition we remove however many
                    # more Context.run adds.
                    tb = task_exc.__traceback__
                    for _ in range(1 + CONTEXT_RUN_TB_FRAMES):
                        if tb is not None:  # pragma: no branch
                            tb = tb.tb_next
                    final_outcome = Error(task_exc.with_traceback(tb))
                    # Remove local refs so that e.g. cancelled coroutine locals
                    # are not kept alive by this frame until another exception
                    # comes along.
                    del tb

                if final_outcome is not None:
                    # We can't call this directly inside the except: blocks
                    # above, because then the exceptions end up attaching
                    # themselves to other exceptions as __context__ in
                    # unwanted ways.
                    runner.task_exited(task, final_outcome)
                    # final_outcome may contain a traceback ref. It's not as
                    # crucial compared to the above, but this will allow more
                    # prompt release of resources in coroutine locals.
                    final_outcome = None
                else:
                    task._schedule_points += 1
                    if msg is CancelShieldedCheckpoint:
                        runner.reschedule(task)
                    elif type(msg) is WaitTaskRescheduled:
                        task._cancel_points += 1
                        task._abort_func = msg.abort_func
                        # KI is "outside" all cancel scopes, so check for it
                        # before checking for regular cancellation:
                        if runner.ki_pending and task is runner.main_task:
                            task._attempt_delivery_of_pending_ki()
                        task._attempt_delivery_of_any_pending_cancel()
                    elif type(msg) is PermanentlyDetachCoroutineObject:
                        # Pretend the task just exited with the given outcome
                        runner.task_exited(task, msg.final_outcome)
                    else:
                        exc = TypeError(
                            f"trio.run received unrecognized yield message {msg!r}. "
                            "Are you trying to use a library written for some "
                            "other framework like asyncio? That won't work "
                            "without some kind of compatibility shim."
                        )
                        # The foreign library probably doesn't adhere to our
                        # protocol of unwrapping whatever outcome gets sent in.
                        # Instead, we'll arrange to throw `exc` in directly,
                        # which works for at least asyncio and curio.
                        runner.reschedule(task, exc)  # type: ignore[arg-type]
                        task._next_send_fn = task.coro.throw
                    # prevent long-lived reference
                    # TODO: develop test for this deletion
                    del msg

                if "after_task_step" in runner.instruments:
                    runner.instruments.call("after_task_step", task)
                del GLOBAL_RUN_CONTEXT.task
                # prevent long-lived references
                # TODO: develop test for this deletion
                del task, next_send, next_send_fn

    except GeneratorExit:
        # The run-loop generator has been garbage collected without finishing
        warnings.warn(
            RuntimeWarning(
                "Trio guest run got abandoned without properly finishing... "
                "weird stuff might happen"
            ),
            stacklevel=1,
        )
    except TrioInternalError:
        raise
    except BaseException as exc:
        raise TrioInternalError("internal error in Trio - please file a bug!") from exc
    finally:
        GLOBAL_RUN_CONTEXT.__dict__.clear()
        runner.close()
        # Have to do this after runner.close() has disabled KI protection,
        # because otherwise there's a race where ki_pending could get set
        # after we check it.
        if runner.ki_pending:
            ki = KeyboardInterrupt()
            if isinstance(runner.main_task_outcome, Error):
                ki.__context__ = runner.main_task_outcome.error
            runner.main_task_outcome = Error(ki)


################################################################
# Other public API functions
################################################################


class _TaskStatusIgnored(TaskStatus[Any]):
    def __repr__(self) -> str:
        return "TASK_STATUS_IGNORED"

    def started(self, value: Any = None) -> None:
        pass


TASK_STATUS_IGNORED: Final[TaskStatus[Any]] = _TaskStatusIgnored()


def current_task() -> Task:
    """Return the :class:`Task` object representing the current task.

    Returns:
      Task: the :class:`Task` that called :func:`current_task`.

    """

    try:
        return GLOBAL_RUN_CONTEXT.task
    except AttributeError:
        raise RuntimeError("must be called from async context") from None


def current_effective_deadline() -> float:
    """Returns the current effective deadline for the current task.

    This function examines all the cancellation scopes that are currently in
    effect (taking into account shielding), and returns the deadline that will
    expire first.

    One example of where this might be is useful is if your code is trying to
    decide whether to begin an expensive operation like an RPC call, but wants
    to skip it if it knows that it can't possibly complete in the available
    time. Another example would be if you're using a protocol like gRPC that
    `propagates timeout information to the remote peer
    <http://www.grpc.io/docs/guides/concepts.html#deadlines>`__; this function
    gives a way to fetch that information so you can send it along.

    If this is called in a context where a cancellation is currently active
    (i.e., a blocking call will immediately raise :exc:`Cancelled`), then
    returned deadline is ``-inf``. If it is called in a context where no
    scopes have a deadline set, it returns ``inf``.

    Returns:
        float: the effective deadline, as an absolute time.

    """
    return current_task()._cancel_status.effective_deadline()


async def checkpoint() -> None:
    """A pure :ref:`checkpoint <checkpoints>`.

    This checks for cancellation and allows other tasks to be scheduled,
    without otherwise blocking.

    Note that the scheduler has the option of ignoring this and continuing to
    run the current task if it decides this is appropriate (e.g. for increased
    efficiency).

    Equivalent to ``await trio.sleep(0)`` (which is implemented by calling
    :func:`checkpoint`.)

    """
    # The scheduler is what checks timeouts and converts them into
    # cancellations. So by doing the schedule point first, we ensure that the
    # cancel point has the most up-to-date info.
    await cancel_shielded_checkpoint()
    task = current_task()
    task._cancel_points += 1
    if task._cancel_status.effectively_cancelled or (
        task is task._runner.main_task and task._runner.ki_pending
    ):
        with CancelScope(deadline=-inf):
            await _core.wait_task_rescheduled(lambda _: _core.Abort.SUCCEEDED)


async def checkpoint_if_cancelled() -> None:
    """Issue a :ref:`checkpoint <checkpoints>` if the calling context has been
    cancelled.

    Equivalent to (but potentially more efficient than)::

        if trio.current_effective_deadline() == -inf:
            await trio.lowlevel.checkpoint()

    This is either a no-op, or else it allow other tasks to be scheduled and
    then raises :exc:`trio.Cancelled`.

    Typically used together with :func:`cancel_shielded_checkpoint`.

    """
    task = current_task()
    if task._cancel_status.effectively_cancelled or (
        task is task._runner.main_task and task._runner.ki_pending
    ):
        await _core.checkpoint()
        raise AssertionError("this should never happen")  # pragma: no cover
    task._cancel_points += 1


if sys.platform == "win32":
    from ._generated_io_windows import *
    from ._io_windows import (
        EventResult as EventResult,
        WindowsIOManager as TheIOManager,
        _WindowsStatistics as IOStatistics,
    )
elif sys.platform == "linux" or (not TYPE_CHECKING and hasattr(select, "epoll")):
    from ._generated_io_epoll import *
    from ._io_epoll import (
        EpollIOManager as TheIOManager,
        EventResult as EventResult,
        _EpollStatistics as IOStatistics,
    )
elif TYPE_CHECKING or hasattr(select, "kqueue"):
    from ._generated_io_kqueue import *
    from ._io_kqueue import (
        EventResult as EventResult,
        KqueueIOManager as TheIOManager,
        _KqueueStatistics as IOStatistics,
    )
else:  # pragma: no cover
    raise NotImplementedError("unsupported platform")

from ._generated_instrumentation import *
from ._generated_run import *
