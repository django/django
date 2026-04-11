from __future__ import annotations

import contextlib
import contextvars
import inspect
import queue as stdlib_queue
import threading
from itertools import count
from typing import TYPE_CHECKING, Generic, TypeVar

import attrs
import outcome
from attrs import define
from sniffio import current_async_library_cvar

import trio

from ._core import (
    RunVar,
    TrioToken,
    checkpoint,
    disable_ki_protection,
    enable_ki_protection,
    start_thread_soon,
)
from ._sync import CapacityLimiter, Event
from ._util import coroutine_or_error

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Generator

    from typing_extensions import TypeVarTuple, Unpack

    from trio._core._traps import RaiseCancelT

    Ts = TypeVarTuple("Ts")

RetT = TypeVar("RetT")


class _ParentTaskData(threading.local):
    """Global due to Threading API, thread local storage for data related to the
    parent task of native Trio threads."""

    token: TrioToken
    abandon_on_cancel: bool
    cancel_register: list[RaiseCancelT | None]
    task_register: list[trio.lowlevel.Task | None]


PARENT_TASK_DATA = _ParentTaskData()

_limiter_local: RunVar[CapacityLimiter] = RunVar("limiter")
# I pulled this number out of the air; it isn't based on anything. Probably we
# should make some kind of measurements to pick a good value.
DEFAULT_LIMIT = 40
_thread_counter = count()


@define
class _ActiveThreadCount:
    count: int
    event: Event


_active_threads_local: RunVar[_ActiveThreadCount] = RunVar("active_threads")


@contextlib.contextmanager
def _track_active_thread() -> Generator[None, None, None]:
    try:
        active_threads_local = _active_threads_local.get()
    except LookupError:
        active_threads_local = _ActiveThreadCount(0, Event())
        _active_threads_local.set(active_threads_local)

    active_threads_local.count += 1
    try:
        yield
    finally:
        active_threads_local.count -= 1
        if active_threads_local.count == 0:
            active_threads_local.event.set()
            active_threads_local.event = Event()


async def wait_all_threads_completed() -> None:
    """Wait until no threads are still running tasks.

    This is intended to be used when testing code with trio.to_thread to
    make sure no tasks are still making progress in a thread. See the
    following code for a usage example::

        async def wait_all_settled():
            while True:
                await trio.testing.wait_all_threads_complete()
                await trio.testing.wait_all_tasks_blocked()
                if trio.testing.active_thread_count() == 0:
                    break
    """

    await checkpoint()

    try:
        active_threads_local = _active_threads_local.get()
    except LookupError:
        # If there would have been active threads, the
        # _active_threads_local would have been set
        return

    while active_threads_local.count != 0:
        await active_threads_local.event.wait()


def active_thread_count() -> int:
    """Returns the number of threads that are currently running a task

    See `trio.testing.wait_all_threads_completed`
    """
    try:
        return _active_threads_local.get().count
    except LookupError:
        return 0


def current_default_thread_limiter() -> CapacityLimiter:
    """Get the default `~trio.CapacityLimiter` used by
    `trio.to_thread.run_sync`.

    The most common reason to call this would be if you want to modify its
    :attr:`~trio.CapacityLimiter.total_tokens` attribute.

    """
    try:
        limiter = _limiter_local.get()
    except LookupError:
        limiter = CapacityLimiter(DEFAULT_LIMIT)
        _limiter_local.set(limiter)
    return limiter


# Eventually we might build this into a full-fledged deadlock-detection
# system; see https://github.com/python-trio/trio/issues/182
# But for now we just need an object to stand in for the thread, so we can
# keep track of who's holding the CapacityLimiter's token.
@attrs.frozen(eq=False, slots=False)
class ThreadPlaceholder:
    name: str


# Types for the to_thread_run_sync message loop
@attrs.frozen(eq=False, slots=False)
class Run(Generic[RetT]):  # type: ignore[explicit-any]
    afn: Callable[..., Awaitable[RetT]]  # type: ignore[explicit-any]
    args: tuple[object, ...]
    context: contextvars.Context = attrs.field(
        init=False,
        factory=contextvars.copy_context,
    )
    queue: stdlib_queue.SimpleQueue[outcome.Outcome[RetT]] = attrs.field(
        init=False,
        factory=stdlib_queue.SimpleQueue,
    )

    @disable_ki_protection
    async def unprotected_afn(self) -> RetT:
        coro = coroutine_or_error(self.afn, *self.args)
        return await coro

    async def run(self) -> None:
        # we use extra checkpoints to pick up and reset any context changes
        task = trio.lowlevel.current_task()
        old_context = task.context
        task.context = self.context.copy()
        await trio.lowlevel.cancel_shielded_checkpoint()
        result = await outcome.acapture(self.unprotected_afn)
        task.context = old_context
        await trio.lowlevel.cancel_shielded_checkpoint()
        self.queue.put_nowait(result)

    async def run_system(self) -> None:
        result = await outcome.acapture(self.unprotected_afn)
        self.queue.put_nowait(result)

    def run_in_host_task(self, token: TrioToken) -> None:
        task_register = PARENT_TASK_DATA.task_register

        def in_trio_thread() -> None:
            task = task_register[0]
            assert task is not None, "guaranteed by abandon_on_cancel semantics"
            trio.lowlevel.reschedule(task, outcome.Value(self))

        token.run_sync_soon(in_trio_thread)

    def run_in_system_nursery(self, token: TrioToken) -> None:
        def in_trio_thread() -> None:
            try:
                trio.lowlevel.spawn_system_task(
                    self.run_system,
                    name=self.afn,
                    context=self.context,
                )
            except RuntimeError:  # system nursery is closed
                self.queue.put_nowait(
                    outcome.Error(trio.RunFinishedError("system nursery is closed")),
                )

        token.run_sync_soon(in_trio_thread)


@attrs.frozen(eq=False, slots=False)
class RunSync(Generic[RetT]):  # type: ignore[explicit-any]
    fn: Callable[..., RetT]  # type: ignore[explicit-any]
    args: tuple[object, ...]
    context: contextvars.Context = attrs.field(
        init=False,
        factory=contextvars.copy_context,
    )
    queue: stdlib_queue.SimpleQueue[outcome.Outcome[RetT]] = attrs.field(
        init=False,
        factory=stdlib_queue.SimpleQueue,
    )

    @disable_ki_protection
    def unprotected_fn(self) -> RetT:
        ret = self.context.run(self.fn, *self.args)

        if inspect.iscoroutine(ret):
            # Manually close coroutine to avoid RuntimeWarnings
            ret.close()
            raise TypeError(
                "Trio expected a synchronous function, but {!r} appears to be "
                "asynchronous".format(getattr(self.fn, "__qualname__", self.fn)),
            )

        return ret

    def run_sync(self) -> None:
        result = outcome.capture(self.unprotected_fn)
        self.queue.put_nowait(result)

    def run_in_host_task(self, token: TrioToken) -> None:
        task_register = PARENT_TASK_DATA.task_register

        def in_trio_thread() -> None:
            task = task_register[0]
            assert task is not None, "guaranteed by abandon_on_cancel semantics"
            trio.lowlevel.reschedule(task, outcome.Value(self))

        token.run_sync_soon(in_trio_thread)

    def run_in_system_nursery(self, token: TrioToken) -> None:
        token.run_sync_soon(self.run_sync)


@enable_ki_protection
async def to_thread_run_sync(
    sync_fn: Callable[[Unpack[Ts]], RetT],
    *args: Unpack[Ts],
    thread_name: str | None = None,
    abandon_on_cancel: bool = False,
    limiter: CapacityLimiter | None = None,
) -> RetT:
    """Convert a blocking operation into an async operation using a thread.

    These two lines are equivalent::

        sync_fn(*args)
        await trio.to_thread.run_sync(sync_fn, *args)

    except that if ``sync_fn`` takes a long time, then the first line will
    block the Trio loop while it runs, while the second line allows other Trio
    tasks to continue working while ``sync_fn`` runs. This is accomplished by
    pushing the call to ``sync_fn(*args)`` off into a worker thread.

    From inside the worker thread, you can get back into Trio using the
    functions in `trio.from_thread`.

    Args:
      sync_fn: An arbitrary synchronous callable.
      *args: Positional arguments to pass to sync_fn. If you need keyword
          arguments, use :func:`functools.partial`.
      abandon_on_cancel (bool): Whether to abandon this thread upon
          cancellation of this operation. See discussion below.
      thread_name (str): Optional string to set the name of the thread.
          Will always set `threading.Thread.name`, but only set the os name
          if pthread.h is available (i.e. most POSIX installations).
          pthread names are limited to 15 characters, and can be read from
          ``/proc/<PID>/task/<SPID>/comm`` or with ``ps -eT``, among others.
          Defaults to ``{sync_fn.__name__|None} from {trio.lowlevel.current_task().name}``.
      limiter (None, or CapacityLimiter-like object):
          An object used to limit the number of simultaneous threads. Most
          commonly this will be a `~trio.CapacityLimiter`, but it could be
          anything providing compatible
          :meth:`~trio.CapacityLimiter.acquire_on_behalf_of` and
          :meth:`~trio.CapacityLimiter.release_on_behalf_of` methods. This
          function will call ``acquire_on_behalf_of`` before starting the
          thread, and ``release_on_behalf_of`` after the thread has finished.

          If None (the default), uses the default `~trio.CapacityLimiter`, as
          returned by :func:`current_default_thread_limiter`.

    **Cancellation handling**: Cancellation is a tricky issue here, because
    neither Python nor the operating systems it runs on provide any general
    mechanism for cancelling an arbitrary synchronous function running in a
    thread. This function will always check for cancellation on entry, before
    starting the thread. But once the thread is running, there are two ways it
    can handle being cancelled:

    * If ``abandon_on_cancel=False``, the function ignores the cancellation and
      keeps going, just like if we had called ``sync_fn`` synchronously. This
      is the default behavior.

    * If ``abandon_on_cancel=True``, then this function immediately raises
      `~trio.Cancelled`. In this case **the thread keeps running in
      background** – we just abandon it to do whatever it's going to do, and
      silently discard any return value or errors that it raises. Only use
      this if you know that the operation is safe and side-effect free. (For
      example: :func:`trio.socket.getaddrinfo` uses a thread with
      ``abandon_on_cancel=True``, because it doesn't really affect anything if a
      stray hostname lookup keeps running in the background.)

      The ``limiter`` is only released after the thread has *actually*
      finished – which in the case of cancellation may be some time after this
      function has returned. If :func:`trio.run` finishes before the thread
      does, then the limiter release method will never be called at all.

    .. warning::

       You should not use this function to call long-running CPU-bound
       functions! In addition to the usual GIL-related reasons why using
       threads for CPU-bound work is not very effective in Python, there is an
       additional problem: on CPython, `CPU-bound threads tend to "starve out"
       IO-bound threads <https://bugs.python.org/issue7946>`__, so using
       threads for CPU-bound work is likely to adversely affect the main
       thread running Trio. If you need to do this, you're better off using a
       worker process, or perhaps PyPy (which still has a GIL, but may do a
       better job of fairly allocating CPU time between threads).

    Returns:
      Whatever ``sync_fn(*args)`` returns.

    Raises:
      Exception: Whatever ``sync_fn(*args)`` raises.

    """
    await trio.lowlevel.checkpoint_if_cancelled()
    # raise early if abandon_on_cancel.__bool__ raises
    # and give a new name to ensure mypy knows it's never None
    abandon_bool = bool(abandon_on_cancel)
    if limiter is None:
        limiter = current_default_thread_limiter()

    # Holds a reference to the task that's blocked in this function waiting
    # for the result – or None if this function was cancelled and we should
    # discard the result.
    task_register: list[trio.lowlevel.Task | None] = [trio.lowlevel.current_task()]
    # Holds a reference to the raise_cancel function provided if a cancellation
    # is attempted against this task - or None if no such delivery has happened.
    cancel_register: list[RaiseCancelT | None] = [None]  # type: ignore[assignment]
    name = f"trio.to_thread.run_sync-{next(_thread_counter)}"
    placeholder = ThreadPlaceholder(name)

    # This function gets scheduled into the Trio run loop to deliver the
    # thread's result.
    def report_back_in_trio_thread_fn(result: outcome.Outcome[RetT]) -> None:
        def do_release_then_return_result() -> RetT:
            # release_on_behalf_of is an arbitrary user-defined method, so it
            # might raise an error. If it does, we want that error to
            # replace the regular return value, and if the regular return was
            # already an exception then we want them to chain.
            try:
                return result.unwrap()
            finally:
                limiter.release_on_behalf_of(placeholder)

        result = outcome.capture(do_release_then_return_result)
        if task_register[0] is not None:
            trio.lowlevel.reschedule(task_register[0], outcome.Value(result))

    current_trio_token = trio.lowlevel.current_trio_token()

    if thread_name is None:
        thread_name = f"{getattr(sync_fn, '__name__', None)} from {trio.lowlevel.current_task().name}"

    def worker_fn() -> RetT:
        PARENT_TASK_DATA.token = current_trio_token
        PARENT_TASK_DATA.abandon_on_cancel = abandon_bool
        PARENT_TASK_DATA.cancel_register = cancel_register
        PARENT_TASK_DATA.task_register = task_register
        try:
            ret = context.run(sync_fn, *args)

            if inspect.iscoroutine(ret):
                # Manually close coroutine to avoid RuntimeWarnings
                ret.close()
                raise TypeError(
                    "Trio expected a sync function, but {!r} appears to be "
                    "asynchronous".format(getattr(sync_fn, "__qualname__", sync_fn)),
                )

            return ret
        finally:
            del PARENT_TASK_DATA.token
            del PARENT_TASK_DATA.abandon_on_cancel
            del PARENT_TASK_DATA.cancel_register
            del PARENT_TASK_DATA.task_register

    context = contextvars.copy_context()
    # Trio doesn't use current_async_library_cvar, but if someone
    # else set it, it would now shine through since
    # sniffio.thread_local isn't set in the new thread. Make sure
    # the new thread sees that it's not running in async context.
    context.run(current_async_library_cvar.set, None)

    def deliver_worker_fn_result(result: outcome.Outcome[RetT]) -> None:
        # If the entire run finished, the task we're trying to contact is
        # certainly long gone -- it must have been cancelled and abandoned
        # us. Just ignore the error in this case.
        with contextlib.suppress(trio.RunFinishedError):
            current_trio_token.run_sync_soon(report_back_in_trio_thread_fn, result)

    await limiter.acquire_on_behalf_of(placeholder)
    with _track_active_thread():
        try:
            start_thread_soon(worker_fn, deliver_worker_fn_result, thread_name)
        except:
            limiter.release_on_behalf_of(placeholder)
            raise

        def abort(raise_cancel: RaiseCancelT) -> trio.lowlevel.Abort:
            # fill so from_thread_check_cancelled can raise
            # 'raise_cancel' will immediately delete its reason object, so we make
            # a copy in each thread
            cancel_register[0] = raise_cancel
            if abandon_bool:
                # empty so report_back_in_trio_thread_fn cannot reschedule
                task_register[0] = None
                return trio.lowlevel.Abort.SUCCEEDED
            else:
                return trio.lowlevel.Abort.FAILED

        while True:
            # wait_task_rescheduled return value cannot be typed
            msg_from_thread: outcome.Outcome[RetT] | Run[object] | RunSync[object] = (
                await trio.lowlevel.wait_task_rescheduled(abort)
            )
            if isinstance(msg_from_thread, outcome.Outcome):
                return msg_from_thread.unwrap()
            elif isinstance(msg_from_thread, Run):
                await msg_from_thread.run()
            elif isinstance(msg_from_thread, RunSync):
                msg_from_thread.run_sync()
            else:  # pragma: no cover, internal debugging guard TODO: use assert_never
                raise TypeError(
                    f"trio.to_thread.run_sync received unrecognized thread message {msg_from_thread!r}.",
                )
            del msg_from_thread


def from_thread_check_cancelled() -> None:
    """Raise `trio.Cancelled` if the associated Trio task entered a cancelled status.

     Only applicable to threads spawned by `trio.to_thread.run_sync`. Poll to allow
     ``abandon_on_cancel=False`` threads to raise :exc:`~trio.Cancelled` at a suitable
     place, or to end abandoned ``abandon_on_cancel=True`` threads sooner than they may
     otherwise.

    Raises:
        Cancelled: If the corresponding call to `trio.to_thread.run_sync` has had a
            delivery of cancellation attempted against it, regardless of the value of
            ``abandon_on_cancel`` supplied as an argument to it.
        RuntimeError: If this thread is not spawned from `trio.to_thread.run_sync`.

    .. note::

       To be precise, :func:`~trio.from_thread.check_cancelled` checks whether the task
       running :func:`trio.to_thread.run_sync` has ever been cancelled since the last
       time it was running a :func:`trio.from_thread.run` or :func:`trio.from_thread.run_sync`
       function. It may raise `trio.Cancelled` even if a cancellation occurred that was
       later hidden by a modification to `trio.CancelScope.shield` between the cancelled
       `~trio.CancelScope` and :func:`trio.to_thread.run_sync`. This differs from the
       behavior of normal Trio checkpoints, which raise `~trio.Cancelled` only if the
       cancellation is still active when the checkpoint executes. The distinction here is
       *exceedingly* unlikely to be relevant to your application, but we mention it
       for completeness.
    """
    try:
        raise_cancel = PARENT_TASK_DATA.cancel_register[0]
    except AttributeError:
        raise RuntimeError(
            "this thread wasn't created by Trio, can't check for cancellation",
        ) from None
    if raise_cancel is not None:
        raise_cancel()


def _send_message_to_trio(
    trio_token: TrioToken | None,
    message_to_trio: Run[RetT] | RunSync[RetT],
) -> RetT:
    """Shared logic of from_thread functions"""
    token_provided = trio_token is not None

    if not token_provided:
        try:
            trio_token = PARENT_TASK_DATA.token
        except AttributeError:
            raise RuntimeError(
                "this thread wasn't created by Trio, pass kwarg trio_token=...",
            ) from None
    elif not isinstance(trio_token, TrioToken):
        raise RuntimeError("Passed kwarg trio_token is not of type TrioToken")

    # Avoid deadlock by making sure we're not called from Trio thread
    try:
        trio.lowlevel.current_task()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("this is a blocking function; call it from a thread")

    if token_provided or PARENT_TASK_DATA.abandon_on_cancel:
        message_to_trio.run_in_system_nursery(trio_token)
    else:
        message_to_trio.run_in_host_task(trio_token)

    return message_to_trio.queue.get().unwrap()


def from_thread_run(
    afn: Callable[[Unpack[Ts]], Awaitable[RetT]],
    *args: Unpack[Ts],
    trio_token: TrioToken | None = None,
) -> RetT:
    """Run the given async function in the parent Trio thread, blocking until it
    is complete.

    Returns:
      Whatever ``afn(*args)`` returns.

    Returns or raises whatever the given function returns or raises. It
    can also raise exceptions of its own:

    Raises:
        RunFinishedError: if the corresponding call to :func:`trio.run` has
            already completed, or if the run has started its final cleanup phase
            and can no longer spawn new system tasks.
        Cancelled: If the original call to :func:`trio.to_thread.run_sync` is cancelled
            (if *trio_token* is None) or the call to :func:`trio.run` completes
            (if *trio_token* is not None) while ``afn(*args)`` is running,
            then *afn* is likely to raise :exc:`trio.Cancelled`.
        RuntimeError: if you try calling this from inside the Trio thread,
            which would otherwise cause a deadlock, or if no ``trio_token`` was
            provided, and we can't infer one from context.
        TypeError: if ``afn`` is not an asynchronous function.

    **Locating a TrioToken**: There are two ways to specify which
    `trio.run` loop to reenter:

        - Spawn this thread from `trio.to_thread.run_sync`. Trio will
          automatically capture the relevant Trio token and use it
          to re-enter the same Trio task.
        - Pass a keyword argument, ``trio_token`` specifying a specific
          `trio.run` loop to re-enter. This is useful in case you have a
          "foreign" thread, spawned using some other framework, and still want
          to enter Trio, or if you want to use a new system task to call ``afn``,
          maybe to avoid the cancellation context of a corresponding
          `trio.to_thread.run_sync` task. You can get this token from
          :func:`trio.lowlevel.current_trio_token`.
    """
    return _send_message_to_trio(trio_token, Run(afn, args))


def from_thread_run_sync(
    fn: Callable[[Unpack[Ts]], RetT],
    *args: Unpack[Ts],
    trio_token: TrioToken | None = None,
) -> RetT:
    """Run the given sync function in the parent Trio thread, blocking until it
    is complete.

    Returns:
      Whatever ``fn(*args)`` returns.

    Returns or raises whatever the given function returns or raises. It
    can also raise exceptions of its own:

    Raises:
        RunFinishedError: if the corresponding call to `trio.run` has
            already completed.
        RuntimeError: if you try calling this from inside the Trio thread,
            which would otherwise cause a deadlock or if no ``trio_token`` was
            provided, and we can't infer one from context.
        TypeError: if ``fn`` is an async function.

    **Locating a TrioToken**: There are two ways to specify which
    `trio.run` loop to reenter:

        - Spawn this thread from `trio.to_thread.run_sync`. Trio will
          automatically capture the relevant Trio token and use it when you
          want to re-enter Trio.
        - Pass a keyword argument, ``trio_token`` specifying a specific
          `trio.run` loop to re-enter. This is useful in case you have a
          "foreign" thread, spawned using some other framework, and still want
          to enter Trio, or if you want to use a new system task to call ``fn``,
          maybe to avoid the cancellation context of a corresponding
          `trio.to_thread.run_sync` task.
    """
    return _send_message_to_trio(trio_token, RunSync(fn, args))
