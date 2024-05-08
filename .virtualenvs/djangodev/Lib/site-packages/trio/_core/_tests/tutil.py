# Utilities for testing
from __future__ import annotations

import asyncio
import gc
import os
import socket as stdlib_socket
import sys
import warnings
from contextlib import closing, contextmanager
from typing import TYPE_CHECKING, TypeVar

import pytest

# See trio/_tests/conftest.py for the other half of this
from trio._tests.pytest_plugin import RUN_SLOW

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence

slow = pytest.mark.skipif(not RUN_SLOW, reason="use --run-slow to run slow tests")

T = TypeVar("T")

try:
    s = stdlib_socket.socket(stdlib_socket.AF_INET6, stdlib_socket.SOCK_STREAM, 0)
except OSError:  # pragma: no cover
    # Some systems don't even support creating an IPv6 socket, let alone
    # binding it. (ex: Linux with 'ipv6.disable=1' in the kernel command line)
    # We don't have any of those in our CI, and there's nothing that gets
    # tested _only_ if can_create_ipv6 = False, so we'll just no-cover this.
    can_create_ipv6 = False
    can_bind_ipv6 = False
else:
    can_create_ipv6 = True
    with s:
        try:
            s.bind(("::1", 0))
        except OSError:  # pragma: no cover # since support for 3.7 was removed
            can_bind_ipv6 = False
        else:
            can_bind_ipv6 = True

creates_ipv6 = pytest.mark.skipif(not can_create_ipv6, reason="need IPv6")
binds_ipv6 = pytest.mark.skipif(not can_bind_ipv6, reason="need IPv6")


def gc_collect_harder() -> None:
    # In the test suite we sometimes want to call gc.collect() to make sure
    # that any objects with noisy __del__ methods (e.g. unawaited coroutines)
    # get collected before we continue, so their noise doesn't leak into
    # unrelated tests.
    #
    # On PyPy, coroutine objects (for example) can survive at least 1 round of
    # garbage collection, because executing their __del__ method to print the
    # warning can cause them to be resurrected. So we call collect a few times
    # to make sure.
    for _ in range(5):
        gc.collect()


# Some of our tests need to leak coroutines, and thus trigger the
# "RuntimeWarning: coroutine '...' was never awaited" message. This context
# manager should be used anywhere this happens to hide those messages, because
# when expected they're clutter.
@contextmanager
def ignore_coroutine_never_awaited_warnings() -> Generator[None, None, None]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="coroutine '.*' was never awaited")
        try:
            yield
        finally:
            # Make sure to trigger any coroutine __del__ methods now, before
            # we leave the context manager.
            gc_collect_harder()


def _noop(*args: object, **kwargs: object) -> None:
    pass  # pragma: no cover


@contextmanager
def restore_unraisablehook() -> Generator[None, None, None]:
    sys.unraisablehook, prev = sys.__unraisablehook__, sys.unraisablehook
    try:
        yield
    finally:
        sys.unraisablehook = prev


# Used to check sequences that might have some elements out of order.
# Example usage:
# The sequences [1, 2.1, 2.2, 3] and [1, 2.2, 2.1, 3] are both
# matched by the template [1, {2.1, 2.2}, 3]
def check_sequence_matches(seq: Sequence[T], template: Iterable[T | set[T]]) -> None:
    i = 0
    for pattern in template:
        if not isinstance(pattern, set):
            pattern = {pattern}
        got = set(seq[i : i + len(pattern)])
        assert got == pattern
        i += len(got)


# https://bugs.freebsd.org/bugzilla/show_bug.cgi?id=246350
skip_if_fbsd_pipes_broken = pytest.mark.skipif(
    sys.platform != "win32"  # prevent mypy from complaining about missing uname
    and hasattr(os, "uname")
    and os.uname().sysname == "FreeBSD"
    and os.uname().release[:4] < "12.2",
    reason="hangs on FreeBSD 12.1 and earlier, due to FreeBSD bug #246350",
)


def create_asyncio_future_in_new_loop() -> asyncio.Future[object]:
    with closing(asyncio.new_event_loop()) as loop:
        return loop.create_future()
