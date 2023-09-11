from __future__ import annotations

import math
from contextlib import AbstractContextManager, contextmanager
from typing import TYPE_CHECKING

import trio


def move_on_at(deadline: float) -> trio.CancelScope:
    """Use as a context manager to create a cancel scope with the given
    absolute deadline.

    Args:
      deadline (float): The deadline.

    Raises:
      ValueError: if deadline is NaN.

    """
    if math.isnan(deadline):
        raise ValueError("deadline must not be NaN")
    return trio.CancelScope(deadline=deadline)


def move_on_after(seconds: float) -> trio.CancelScope:
    """Use as a context manager to create a cancel scope whose deadline is
    set to now + *seconds*.

    Args:
      seconds (float): The timeout.

    Raises:
      ValueError: if timeout is less than zero or NaN.

    """
    if seconds < 0:
        raise ValueError("timeout must be non-negative")
    return move_on_at(trio.current_time() + seconds)


async def sleep_forever() -> None:
    """Pause execution of the current task forever (or until cancelled).

    Equivalent to calling ``await sleep(math.inf)``.

    """
    await trio.lowlevel.wait_task_rescheduled(lambda _: trio.lowlevel.Abort.SUCCEEDED)


async def sleep_until(deadline: float) -> None:
    """Pause execution of the current task until the given time.

    The difference between :func:`sleep` and :func:`sleep_until` is that the
    former takes a relative time and the latter takes an absolute time
    according to Trio's internal clock (as returned by :func:`current_time`).

    Args:
        deadline (float): The time at which we should wake up again. May be in
            the past, in which case this function executes a checkpoint but
            does not block.

    Raises:
      ValueError: if deadline is NaN.

    """
    with move_on_at(deadline):
        await sleep_forever()


async def sleep(seconds: float) -> None:
    """Pause execution of the current task for the given number of seconds.

    Args:
        seconds (float): The number of seconds to sleep. May be zero to
            insert a checkpoint without actually blocking.

    Raises:
        ValueError: if *seconds* is negative or NaN.

    """
    if seconds < 0:
        raise ValueError("duration must be non-negative")
    if seconds == 0:
        await trio.lowlevel.checkpoint()
    else:
        await sleep_until(trio.current_time() + seconds)


class TooSlowError(Exception):
    """Raised by :func:`fail_after` and :func:`fail_at` if the timeout
    expires.

    """


# workaround for PyCharm not being able to infer return type from @contextmanager
# see https://youtrack.jetbrains.com/issue/PY-36444/PyCharm-doesnt-infer-types-when-using-contextlib.contextmanager-decorator
def fail_at(deadline: float) -> AbstractContextManager[trio.CancelScope]:  # type: ignore[misc]
    """Creates a cancel scope with the given deadline, and raises an error if it
    is actually cancelled.

    This function and :func:`move_on_at` are similar in that both create a
    cancel scope with a given absolute deadline, and if the deadline expires
    then both will cause :exc:`Cancelled` to be raised within the scope. The
    difference is that when the :exc:`Cancelled` exception reaches
    :func:`move_on_at`, it's caught and discarded. When it reaches
    :func:`fail_at`, then it's caught and :exc:`TooSlowError` is raised in its
    place.

    Args:
      deadline (float): The deadline.

    Raises:
      TooSlowError: if a :exc:`Cancelled` exception is raised in this scope
        and caught by the context manager.
      ValueError: if deadline is NaN.

    """
    with move_on_at(deadline) as scope:
        yield scope
    if scope.cancelled_caught:
        raise TooSlowError


if not TYPE_CHECKING:
    fail_at = contextmanager(fail_at)


def fail_after(seconds: float) -> AbstractContextManager[trio.CancelScope]:
    """Creates a cancel scope with the given timeout, and raises an error if
    it is actually cancelled.

    This function and :func:`move_on_after` are similar in that both create a
    cancel scope with a given timeout, and if the timeout expires then both
    will cause :exc:`Cancelled` to be raised within the scope. The difference
    is that when the :exc:`Cancelled` exception reaches :func:`move_on_after`,
    it's caught and discarded. When it reaches :func:`fail_after`, then it's
    caught and :exc:`TooSlowError` is raised in its place.

    Args:
      seconds (float): The timeout.

    Raises:
      TooSlowError: if a :exc:`Cancelled` exception is raised in this scope
        and caught by the context manager.
      ValueError: if *seconds* is less than zero or NaN.

    """
    if seconds < 0:
        raise ValueError("timeout must be non-negative")
    return fail_at(trio.current_time() + seconds)
