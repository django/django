from __future__ import annotations

import math
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, NoReturn

import trio

if TYPE_CHECKING:
    from collections.abc import Generator


def move_on_at(deadline: float, *, shield: bool = False) -> trio.CancelScope:
    """Use as a context manager to create a cancel scope with the given
    absolute deadline.

    Args:
      deadline (float): The deadline.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      ValueError: if deadline is NaN.

    """
    # CancelScope validates that deadline isn't math.nan
    return trio.CancelScope(deadline=deadline, shield=shield)


def move_on_after(
    seconds: float,
    *,
    shield: bool = False,
) -> trio.CancelScope:
    """Use as a context manager to create a cancel scope whose deadline is
    set to now + *seconds*.

    The deadline of the cancel scope is calculated upon entering.

    Args:
      seconds (float): The timeout.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      ValueError: if ``seconds`` is less than zero or NaN.

    """
    # duplicate validation logic to have the correct parameter name
    if seconds < 0:
        raise ValueError("`seconds` must be non-negative")
    if math.isnan(seconds):
        raise ValueError("`seconds` must not be NaN")
    return trio.CancelScope(
        shield=shield,
        relative_deadline=seconds,
    )


async def sleep_forever() -> NoReturn:
    """Pause execution of the current task forever (or until cancelled).

    Equivalent to calling ``await sleep(math.inf)``, except that if manually
    rescheduled this will raise a `RuntimeError`.

    Raises:
      RuntimeError: if rescheduled

    """
    await trio.lowlevel.wait_task_rescheduled(lambda _: trio.lowlevel.Abort.SUCCEEDED)
    raise RuntimeError("Should never have been rescheduled!")


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
        raise ValueError("`seconds` must be non-negative")
    if seconds == 0:
        await trio.lowlevel.checkpoint()
    else:
        await sleep_until(trio.current_time() + seconds)


class TooSlowError(Exception):
    """Raised by :func:`fail_after` and :func:`fail_at` if the timeout
    expires.

    """


@contextmanager
def fail_at(
    deadline: float,
    *,
    shield: bool = False,
) -> Generator[trio.CancelScope, None, None]:
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
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      TooSlowError: if a :exc:`Cancelled` exception is raised in this scope
        and caught by the context manager.
      ValueError: if deadline is NaN.

    """
    with move_on_at(deadline, shield=shield) as scope:
        yield scope
    if scope.cancelled_caught:
        raise TooSlowError


@contextmanager
def fail_after(
    seconds: float,
    *,
    shield: bool = False,
) -> Generator[trio.CancelScope, None, None]:
    """Creates a cancel scope with the given timeout, and raises an error if
    it is actually cancelled.

    This function and :func:`move_on_after` are similar in that both create a
    cancel scope with a given timeout, and if the timeout expires then both
    will cause :exc:`Cancelled` to be raised within the scope. The difference
    is that when the :exc:`Cancelled` exception reaches :func:`move_on_after`,
    it's caught and discarded. When it reaches :func:`fail_after`, then it's
    caught and :exc:`TooSlowError` is raised in its place.

    The deadline of the cancel scope is calculated upon entering.

    Args:
      seconds (float): The timeout.
      shield (bool): Initial value for the `~trio.CancelScope.shield` attribute
          of the newly created cancel scope.

    Raises:
      TooSlowError: if a :exc:`Cancelled` exception is raised in this scope
        and caught by the context manager.
      ValueError: if *seconds* is less than zero or NaN.

    """
    with move_on_after(seconds, shield=shield) as scope:
        yield scope
    if scope.cancelled_caught:
        raise TooSlowError


# Users don't need to know that fail_at & fail_after wraps move_on_at and move_on_after
# and there is no functional difference. So we replace the return value when generating
# documentation.
if "sphinx.ext.autodoc" in sys.modules:
    import inspect

    for c in (fail_at, fail_after):
        c.__signature__ = inspect.Signature.from_callable(c).replace(return_annotation=trio.CancelScope)  # type: ignore[union-attr]
