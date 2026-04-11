from __future__ import annotations

import signal
import sys
import weakref
from typing import TYPE_CHECKING, Generic, Protocol, TypeGuard, TypeVar

import attrs

from .._util import is_main_thread
from ._run_context import GLOBAL_RUN_CONTEXT

if TYPE_CHECKING:
    import types
    from collections.abc import Callable

    from typing_extensions import Self
# In ordinary single-threaded Python code, when you hit control-C, it raises
# an exception and automatically does all the regular unwinding stuff.
#
# In Trio code, we would like hitting control-C to raise an exception and
# automatically do all the regular unwinding stuff. In particular, we would
# like to maintain our invariant that all tasks always run to completion (one
# way or another), by unwinding all of them.
#
# But it's basically impossible to write the core task running code in such a
# way that it can maintain this invariant in the face of KeyboardInterrupt
# exceptions arising at arbitrary bytecode positions. Similarly, if a
# KeyboardInterrupt happened at the wrong moment inside pretty much any of our
# inter-task synchronization or I/O primitives, then the system state could
# get corrupted and prevent our being able to clean up properly.
#
# So, we need a way to defer KeyboardInterrupt processing from these critical
# sections.
#
# Things that don't work:
#
# - Listen for SIGINT and process it in a system task: works fine for
#   well-behaved programs that regularly pass through the event loop, but if
#   user-code goes into an infinite loop then it can't be interrupted. Which
#   is unfortunate, since dealing with infinite loops is what
#   KeyboardInterrupt is for!
#
# - Use pthread_sigmask to disable signal delivery during critical section:
#   (a) windows has no pthread_sigmask, (b) python threads start with all
#   signals unblocked, so if there are any threads around they'll receive the
#   signal and then tell the main thread to run the handler, even if the main
#   thread has that signal blocked.
#
# - Install a signal handler which checks a global variable to decide whether
#   to raise the exception immediately (if we're in a non-critical section),
#   or to schedule it on the event loop (if we're in a critical section). The
#   problem here is that it's impossible to transition safely out of user code:
#
#     with keyboard_interrupt_enabled:
#         msg = coro.send(value)
#
#   If this raises a KeyboardInterrupt, it might be because the coroutine got
#   interrupted and has unwound... or it might be the KeyboardInterrupt
#   arrived just *after* 'send' returned, so the coroutine is still running,
#   but we just lost the message it sent. (And worse, in our actual task
#   runner, the send is hidden inside a utility function etc.)
#
# Solution:
#
# Mark *stack frames* as being interrupt-safe or interrupt-unsafe, and from
# the signal handler check which kind of frame we're currently in when
# deciding whether to raise or schedule the exception.
#
# There are still some cases where this can fail, like if someone hits
# control-C while the process is in the event loop, and then it immediately
# enters an infinite loop in user code. In this case the user has to hit
# control-C a second time. And of course if the user code is written so that
# it doesn't actually exit after a task crashes and everything gets cancelled,
# then there's not much to be done. (Hitting control-C repeatedly might help,
# but in general the solution is to kill the process some other way, just like
# for any Python program that's written to catch and ignore
# KeyboardInterrupt.)

_T = TypeVar("_T")


class _IdRef(weakref.ref[_T]):
    __slots__ = ("_hash",)
    _hash: int

    def __new__(
        cls,
        ob: _T,
        callback: Callable[[Self], object] | None = None,
        /,
    ) -> Self:
        self: Self = weakref.ref.__new__(cls, ob, callback)
        self._hash = object.__hash__(ob)
        return self

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True

        if not isinstance(other, _IdRef):
            return NotImplemented

        my_obj = None
        try:
            my_obj = self()
            return my_obj is not None and my_obj is other()
        finally:
            del my_obj

    # we're overriding a builtin so we do need this
    def __ne__(self, other: object) -> bool:
        return not self == other

    def __hash__(self) -> int:
        return self._hash


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


# see also: https://github.com/python/cpython/issues/88306
class WeakKeyIdentityDictionary(Generic[_KT, _VT]):
    def __init__(self) -> None:
        self._data: dict[_IdRef[_KT], _VT] = {}

        def remove(
            k: _IdRef[_KT],
            selfref: weakref.ref[
                WeakKeyIdentityDictionary[_KT, _VT]
            ] = weakref.ref(  # noqa: B008  # function-call-in-default-argument
                self,
            ),
        ) -> None:
            self = selfref()
            if self is not None:
                try:  # noqa: SIM105  # suppressible-exception
                    del self._data[k]
                except KeyError:
                    pass

        self._remove = remove

    def __getitem__(self, k: _KT) -> _VT:
        return self._data[_IdRef(k)]

    def __setitem__(self, k: _KT, v: _VT) -> None:
        self._data[_IdRef(k, self._remove)] = v


_CODE_KI_PROTECTION_STATUS_WMAP: WeakKeyIdentityDictionary[
    types.CodeType,
    bool,
] = WeakKeyIdentityDictionary()


# This is to support the async_generator package necessary for aclosing on <3.10
# functions decorated @async_generator are given this magic property that's a
# reference to the object itself
# see python-trio/async_generator/async_generator/_impl.py
def legacy_isasyncgenfunction(
    obj: object,
) -> TypeGuard[Callable[..., types.AsyncGeneratorType[object, object]]]:
    return getattr(obj, "_async_gen_function", None) == id(obj)


# NB: according to the signal.signal docs, 'frame' can be None on entry to
# this function:
def ki_protection_enabled(frame: types.FrameType | None) -> bool:
    try:
        task = GLOBAL_RUN_CONTEXT.task
    except AttributeError:
        task_ki_protected = False
        task_frame = None
    else:
        task_ki_protected = task._ki_protected
        task_frame = task.coro.cr_frame

    while frame is not None:
        try:
            v = _CODE_KI_PROTECTION_STATUS_WMAP[frame.f_code]
        except KeyError:
            pass
        else:
            return bool(v)
        if frame.f_code.co_name == "__del__":
            return True
        if frame is task_frame:
            return task_ki_protected
        frame = frame.f_back
    return True


def currently_ki_protected() -> bool:
    r"""Check whether the calling code has :exc:`KeyboardInterrupt` protection
    enabled.

    It's surprisingly easy to think that one's :exc:`KeyboardInterrupt`
    protection is enabled when it isn't, or vice-versa. This function tells
    you what Trio thinks of the matter, which makes it useful for ``assert``\s
    and unit tests.

    Returns:
      bool: True if protection is enabled, and False otherwise.

    """
    return ki_protection_enabled(sys._getframe())


class _SupportsCode(Protocol):
    __code__: types.CodeType


_T_supports_code = TypeVar("_T_supports_code", bound=_SupportsCode)


def enable_ki_protection(f: _T_supports_code, /) -> _T_supports_code:
    """Decorator to enable KI protection."""
    orig = f

    if legacy_isasyncgenfunction(f):
        f = f.__wrapped__  # type: ignore

    _CODE_KI_PROTECTION_STATUS_WMAP[f.__code__] = True
    return orig


def disable_ki_protection(f: _T_supports_code, /) -> _T_supports_code:
    """Decorator to disable KI protection."""
    orig = f

    if legacy_isasyncgenfunction(f):
        f = f.__wrapped__  # type: ignore

    _CODE_KI_PROTECTION_STATUS_WMAP[f.__code__] = False
    return orig


@attrs.define(slots=False)
class KIManager:
    handler: Callable[[int, types.FrameType | None], None] | None = None

    def install(
        self,
        deliver_cb: Callable[[], object],
        restrict_keyboard_interrupt_to_checkpoints: bool,
    ) -> None:
        assert self.handler is None
        if (
            not is_main_thread()
            or signal.getsignal(signal.SIGINT) != signal.default_int_handler
        ):
            return

        def handler(signum: int, frame: types.FrameType | None) -> None:
            assert signum == signal.SIGINT
            protection_enabled = ki_protection_enabled(frame)
            if protection_enabled or restrict_keyboard_interrupt_to_checkpoints:
                deliver_cb()
            else:
                raise KeyboardInterrupt

        self.handler = handler
        signal.signal(signal.SIGINT, handler)

    def close(self) -> None:
        if self.handler is not None:
            if signal.getsignal(signal.SIGINT) is self.handler:
                signal.signal(signal.SIGINT, signal.default_int_handler)
            self.handler = None
