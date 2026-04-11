import asyncio
import contextlib

# PY3.9: Import Callable from typing until we drop Python 3.9 support
# https://github.com/python/cpython/issues/87131
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

_T = TypeVar("_T")

RE_RAISE_EXCEPTIONS = (SystemExit, KeyboardInterrupt)


def _set_result(wait_next: "asyncio.Future[None]") -> None:
    """Set the result of a future if it is not already done."""
    if not wait_next.done():
        wait_next.set_result(None)


async def _wait_one(
    futures: "Iterable[asyncio.Future[Any]]",
    loop: asyncio.AbstractEventLoop,
) -> _T:
    """Wait for the first future to complete."""
    wait_next = loop.create_future()

    def _on_completion(fut: "asyncio.Future[Any]") -> None:
        if not wait_next.done():
            wait_next.set_result(fut)

    for f in futures:
        f.add_done_callback(_on_completion)

    try:
        return await wait_next
    finally:
        for f in futures:
            f.remove_done_callback(_on_completion)


async def staggered_race(
    coro_fns: Iterable[Callable[[], Awaitable[_T]]],
    delay: Optional[float],
    *,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> Tuple[Optional[_T], Optional[int], List[Optional[BaseException]]]:
    """
    Run coroutines with staggered start times and take the first to finish.

    This method takes an iterable of coroutine functions. The first one is
    started immediately. From then on, whenever the immediately preceding one
    fails (raises an exception), or when *delay* seconds has passed, the next
    coroutine is started. This continues until one of the coroutines complete
    successfully, in which case all others are cancelled, or until all
    coroutines fail.

    The coroutines provided should be well-behaved in the following way:

    * They should only ``return`` if completed successfully.

    * They should always raise an exception if they did not complete
      successfully. In particular, if they handle cancellation, they should
      probably reraise, like this::

        try:
            # do work
        except asyncio.CancelledError:
            # undo partially completed work
            raise

    Args:
    ----
        coro_fns: an iterable of coroutine functions, i.e. callables that
            return a coroutine object when called. Use ``functools.partial`` or
            lambdas to pass arguments.

        delay: amount of time, in seconds, between starting coroutines. If
            ``None``, the coroutines will run sequentially.

        loop: the event loop to use. If ``None``, the running loop is used.

    Returns:
    -------
        tuple *(winner_result, winner_index, exceptions)* where

        - *winner_result*: the result of the winning coroutine, or ``None``
          if no coroutines won.

        - *winner_index*: the index of the winning coroutine in
          ``coro_fns``, or ``None`` if no coroutines won. If the winning
          coroutine may return None on success, *winner_index* can be used
          to definitively determine whether any coroutine won.

        - *exceptions*: list of exceptions returned by the coroutines.
          ``len(exceptions)`` is equal to the number of coroutines actually
          started, and the order is the same as in ``coro_fns``. The winning
          coroutine's entry is ``None``.

    """
    loop = loop or asyncio.get_running_loop()
    exceptions: List[Optional[BaseException]] = []
    tasks: Set[asyncio.Task[Optional[Tuple[_T, int]]]] = set()

    async def run_one_coro(
        coro_fn: Callable[[], Awaitable[_T]],
        this_index: int,
        start_next: "asyncio.Future[None]",
    ) -> Optional[Tuple[_T, int]]:
        """
        Run a single coroutine.

        If the coroutine fails, set the exception in the exceptions list and
        start the next coroutine by setting the result of the start_next.

        If the coroutine succeeds, return the result and the index of the
        coroutine in the coro_fns list.

        If SystemExit or KeyboardInterrupt is raised, re-raise it.
        """
        try:
            result = await coro_fn()
        except RE_RAISE_EXCEPTIONS:
            raise
        except BaseException as e:
            exceptions[this_index] = e
            _set_result(start_next)  # Kickstart the next coroutine
            return None

        return result, this_index

    start_next_timer: Optional[asyncio.TimerHandle] = None
    start_next: Optional[asyncio.Future[None]]
    task: asyncio.Task[Optional[Tuple[_T, int]]]
    done: Union[asyncio.Future[None], asyncio.Task[Optional[Tuple[_T, int]]]]
    coro_iter = iter(coro_fns)
    this_index = -1
    try:
        while True:
            if coro_fn := next(coro_iter, None):
                this_index += 1
                exceptions.append(None)
                start_next = loop.create_future()
                task = loop.create_task(run_one_coro(coro_fn, this_index, start_next))
                tasks.add(task)
                start_next_timer = (
                    loop.call_later(delay, _set_result, start_next) if delay else None
                )
            elif not tasks:
                # We exhausted the coro_fns list and no tasks are running
                # so we have no winner and all coroutines failed.
                break

            while tasks or start_next:
                done = await _wait_one(
                    (*tasks, start_next) if start_next else tasks, loop
                )
                if done is start_next:
                    # The current task has failed or the timer has expired
                    # so we need to start the next task.
                    start_next = None
                    if start_next_timer:
                        start_next_timer.cancel()
                        start_next_timer = None

                    # Break out of the task waiting loop to start the next
                    # task.
                    break

                if TYPE_CHECKING:
                    assert isinstance(done, asyncio.Task)

                tasks.remove(done)
                if winner := done.result():
                    return *winner, exceptions
    finally:
        # We either have:
        #  - a winner
        #  - all tasks failed
        #  - a KeyboardInterrupt or SystemExit.

        #
        # If the timer is still running, cancel it.
        #
        if start_next_timer:
            start_next_timer.cancel()

        #
        # If there are any tasks left, cancel them and than
        # wait them so they fill the exceptions list.
        #
        for task in tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return None, None, exceptions
