from __future__ import annotations

import errno
import select
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Iterator, Literal

import attr
import outcome

from .. import _core
from ._run import _public
from ._wakeup_socketpair import WakeupSocketpair

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from .._core import Abort, RaiseCancelT, Task, UnboundedQueue
    from .._file_io import _HasFileNo

assert not TYPE_CHECKING or (sys.platform != "linux" and sys.platform != "win32")

EventResult: TypeAlias = "list[select.kevent]"


@attr.s(slots=True, eq=False, frozen=True)
class _KqueueStatistics:
    tasks_waiting: int = attr.ib()
    monitors: int = attr.ib()
    backend: Literal["kqueue"] = attr.ib(init=False, default="kqueue")


@attr.s(slots=True, eq=False)
class KqueueIOManager:
    _kqueue: select.kqueue = attr.ib(factory=select.kqueue)
    # {(ident, filter): Task or UnboundedQueue}
    _registered: dict[tuple[int, int], Task | UnboundedQueue[select.kevent]] = attr.ib(
        factory=dict
    )
    _force_wakeup: WakeupSocketpair = attr.ib(factory=WakeupSocketpair)
    _force_wakeup_fd: int | None = attr.ib(default=None)

    def __attrs_post_init__(self) -> None:
        force_wakeup_event = select.kevent(
            self._force_wakeup.wakeup_sock, select.KQ_FILTER_READ, select.KQ_EV_ADD
        )
        self._kqueue.control([force_wakeup_event], 0)
        self._force_wakeup_fd = self._force_wakeup.wakeup_sock.fileno()

    def statistics(self) -> _KqueueStatistics:
        tasks_waiting = 0
        monitors = 0
        for receiver in self._registered.values():
            if type(receiver) is _core.Task:
                tasks_waiting += 1
            else:
                monitors += 1
        return _KqueueStatistics(tasks_waiting=tasks_waiting, monitors=monitors)

    def close(self) -> None:
        self._kqueue.close()
        self._force_wakeup.close()

    def force_wakeup(self) -> None:
        self._force_wakeup.wakeup_thread_and_signal_safe()

    def get_events(self, timeout: float) -> EventResult:
        # max_events must be > 0 or kqueue gets cranky
        # and we generally want this to be strictly larger than the actual
        # number of events we get, so that we can tell that we've gotten
        # all the events in just 1 call.
        max_events = len(self._registered) + 1
        events = []
        while True:
            batch = self._kqueue.control([], max_events, timeout)
            events += batch
            if len(batch) < max_events:
                break
            else:
                timeout = 0
                # and loop back to the start
        return events

    def process_events(self, events: EventResult) -> None:
        for event in events:
            key = (event.ident, event.filter)
            if event.ident == self._force_wakeup_fd:
                self._force_wakeup.drain()
                continue
            receiver = self._registered[key]
            if event.flags & select.KQ_EV_ONESHOT:
                del self._registered[key]
            if isinstance(receiver, _core.Task):
                _core.reschedule(receiver, outcome.Value(event))
            else:
                receiver.put_nowait(event)

    # kevent registration is complicated -- e.g. aio submission can
    # implicitly perform a EV_ADD, and EVFILT_PROC with NOTE_TRACK will
    # automatically register filters for child processes. So our lowlevel
    # API is *very* low-level: we expose the kqueue itself for adding
    # events or sticking into AIO submission structs, and split waiting
    # off into separate methods. It's your responsibility to make sure
    # that handle_io never receives an event without a corresponding
    # registration! This may be challenging if you want to be careful
    # about e.g. KeyboardInterrupt. Possibly this API could be improved to
    # be more ergonomic...

    @_public
    def current_kqueue(self) -> select.kqueue:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__.
        """
        return self._kqueue

    @contextmanager
    @_public
    def monitor_kevent(
        self, ident: int, filter: int
    ) -> Iterator[_core.UnboundedQueue[select.kevent]]:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__.
        """
        key = (ident, filter)
        if key in self._registered:
            raise _core.BusyResourceError(
                "attempt to register multiple listeners for same ident/filter pair"
            )
        q = _core.UnboundedQueue[select.kevent]()
        self._registered[key] = q
        try:
            yield q
        finally:
            del self._registered[key]

    @_public
    async def wait_kevent(
        self, ident: int, filter: int, abort_func: Callable[[RaiseCancelT], Abort]
    ) -> Abort:
        """TODO: these are implemented, but are currently more of a sketch than
        anything real. See `#26
        <https://github.com/python-trio/trio/issues/26>`__.
        """
        key = (ident, filter)
        if key in self._registered:
            raise _core.BusyResourceError(
                "attempt to register multiple listeners for same ident/filter pair"
            )
        self._registered[key] = _core.current_task()

        def abort(raise_cancel: RaiseCancelT) -> Abort:
            r = abort_func(raise_cancel)
            if r is _core.Abort.SUCCEEDED:
                del self._registered[key]
            return r

        # wait_task_rescheduled does not have its return type typed
        return await _core.wait_task_rescheduled(abort)  # type: ignore[no-any-return]

    async def _wait_common(self, fd: int | _HasFileNo, filter: int) -> None:
        if not isinstance(fd, int):
            fd = fd.fileno()
        flags = select.KQ_EV_ADD | select.KQ_EV_ONESHOT
        event = select.kevent(fd, filter, flags)
        self._kqueue.control([event], 0)

        def abort(_: RaiseCancelT) -> Abort:
            event = select.kevent(fd, filter, select.KQ_EV_DELETE)
            try:
                self._kqueue.control([event], 0)
            except OSError as exc:
                # kqueue tracks individual fds (*not* the underlying file
                # object, see _io_epoll.py for a long discussion of why this
                # distinction matters), and automatically deregisters an event
                # if the fd is closed. So if kqueue.control says that it
                # doesn't know about this event, then probably it's because
                # the fd was closed behind our backs. (Too bad we can't ask it
                # to wake us up when this happens, versus discovering it after
                # the fact... oh well, you can't have everything.)
                #
                # FreeBSD reports this using EBADF. macOS uses ENOENT.
                if exc.errno in (errno.EBADF, errno.ENOENT):  # pragma: no branch
                    pass
                else:  # pragma: no cover
                    # As far as we know, this branch can't happen.
                    raise
            return _core.Abort.SUCCEEDED

        await self.wait_kevent(fd, filter, abort)

    @_public
    async def wait_readable(self, fd: int | _HasFileNo) -> None:
        """Block until the kernel reports that the given object is readable.

        On Unix systems, ``fd`` must either be an integer file descriptor,
        or else an object with a ``.fileno()`` method which returns an
        integer file descriptor. Any kind of file descriptor can be passed,
        though the exact semantics will depend on your kernel. For example,
        this probably won't do anything useful for on-disk files.

        On Windows systems, ``fd`` must either be an integer ``SOCKET``
        handle, or else an object with a ``.fileno()`` method which returns
        an integer ``SOCKET`` handle. File descriptors aren't supported,
        and neither are handles that refer to anything besides a
        ``SOCKET``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become readable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._wait_common(fd, select.KQ_FILTER_READ)

    @_public
    async def wait_writable(self, fd: int | _HasFileNo) -> None:
        """Block until the kernel reports that the given object is writable.

        See `wait_readable` for the definition of ``fd``.

        :raises trio.BusyResourceError:
            if another task is already waiting for the given socket to
            become writable.
        :raises trio.ClosedResourceError:
            if another task calls :func:`notify_closing` while this
            function is still working.
        """
        await self._wait_common(fd, select.KQ_FILTER_WRITE)

    @_public
    def notify_closing(self, fd: int | _HasFileNo) -> None:
        """Notify waiters of the given object that it will be closed.

        Call this before closing a file descriptor (on Unix) or socket (on
        Windows). This will cause any `wait_readable` or `wait_writable`
        calls on the given object to immediately wake up and raise
        `~trio.ClosedResourceError`.

        This doesn't actually close the object – you still have to do that
        yourself afterwards. Also, you want to be careful to make sure no
        new tasks start waiting on the object in between when you call this
        and when it's actually closed. So to close something properly, you
        usually want to do these steps in order:

        1. Explicitly mark the object as closed, so that any new attempts
           to use it will abort before they start.
        2. Call `notify_closing` to wake up any already-existing users.
        3. Actually close the object.

        It's also possible to do them in a different order if that's more
        convenient, *but only if* you make sure not to have any checkpoints in
        between the steps. This way they all happen in a single atomic
        step, so other tasks won't be able to tell what order they happened
        in anyway.
        """
        if not isinstance(fd, int):
            fd = fd.fileno()

        for filter in [select.KQ_FILTER_READ, select.KQ_FILTER_WRITE]:
            key = (fd, filter)
            receiver = self._registered.get(key)

            if receiver is None:
                continue

            if type(receiver) is _core.Task:
                event = select.kevent(fd, filter, select.KQ_EV_DELETE)
                self._kqueue.control([event], 0)
                exc = _core.ClosedResourceError("another task closed this fd")
                _core.reschedule(receiver, outcome.Error(exc))
                del self._registered[key]
            else:
                # XX this is an interesting example of a case where being able
                # to close a queue would be useful...
                raise NotImplementedError(
                    "can't close an fd that monitor_kevent is using"
                )
