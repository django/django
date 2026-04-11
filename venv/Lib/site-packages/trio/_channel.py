from __future__ import annotations

import sys
from collections import OrderedDict, deque
from collections.abc import AsyncGenerator, Callable  # noqa: TC003  # Needed for Sphinx
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import wraps
from math import inf
from typing import (
    TYPE_CHECKING,
    Generic,
)

import attrs
from outcome import Error, Value

import trio

from ._abc import ReceiveChannel, ReceiveType, SendChannel, SendType, T
from ._core import Abort, BrokenResourceError, RaiseCancelT, Task, enable_ki_protection
from ._util import (
    MultipleExceptionError,
    NoPublicConstructor,
    final,
    raise_single_exception_from_group,
)

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import ParamSpec, Self

    P = ParamSpec("P")
elif "sphinx.ext.autodoc" in sys.modules:
    # P needs to exist for Sphinx to parse the type hints successfully.
    try:
        from typing_extensions import ParamSpec
    except ImportError:
        P = ...  # This is valid in Callable, though not correct
    else:
        P = ParamSpec("P")


# written as a class so you can say open_memory_channel[int](5)
@final
class open_memory_channel(tuple["MemorySendChannel[T]", "MemoryReceiveChannel[T]"]):
    """Open a channel for passing objects between tasks within a process.

    Memory channels are lightweight, cheap to allocate, and entirely
    in-memory. They don't involve any operating-system resources, or any kind
    of serialization. They just pass Python objects directly between tasks
    (with a possible stop in an internal buffer along the way).

    Channel objects can be closed by calling `~trio.abc.AsyncResource.aclose`
    or using ``async with``. They are *not* automatically closed when garbage
    collected. Closing memory channels isn't mandatory, but it is generally a
    good idea, because it helps avoid situations where tasks get stuck waiting
    on a channel when there's no-one on the other side. See
    :ref:`channel-shutdown` for details.

    Memory channel operations are all atomic with respect to
    cancellation, either `~trio.abc.ReceiveChannel.receive` will
    successfully return an object, or it will raise :exc:`Cancelled`
    while leaving the channel unchanged.

    Args:
      max_buffer_size (int or math.inf): The maximum number of items that can
        be buffered in the channel before :meth:`~trio.abc.SendChannel.send`
        blocks. Choosing a sensible value here is important to ensure that
        backpressure is communicated promptly and avoid unnecessary latency;
        see :ref:`channel-buffering` for more details. If in doubt, use 0.

    Returns:
      A pair ``(send_channel, receive_channel)``. If you have
      trouble remembering which order these go in, remember: data
      flows from left → right.

    In addition to the standard channel methods, all memory channel objects
    provide a ``statistics()`` method, which returns an object with the
    following fields:

    * ``current_buffer_used``: The number of items currently stored in the
      channel buffer.
    * ``max_buffer_size``: The maximum number of items allowed in the buffer,
      as passed to :func:`open_memory_channel`.
    * ``open_send_channels``: The number of open
      :class:`MemorySendChannel` endpoints pointing to this channel.
      Initially 1, but can be increased by
      :meth:`MemorySendChannel.clone`.
    * ``open_receive_channels``: Likewise, but for open
      :class:`MemoryReceiveChannel` endpoints.
    * ``tasks_waiting_send``: The number of tasks blocked in ``send`` on this
      channel (summing over all clones).
    * ``tasks_waiting_receive``: The number of tasks blocked in ``receive`` on
      this channel (summing over all clones).
    """

    def __new__(  # type: ignore[misc]  # "must return a subtype"
        cls,
        max_buffer_size: int | float,  # noqa: PYI041
    ) -> tuple[MemorySendChannel[T], MemoryReceiveChannel[T]]:
        if max_buffer_size != inf and not isinstance(max_buffer_size, int):
            raise TypeError("max_buffer_size must be an integer or math.inf")
        if max_buffer_size < 0:
            raise ValueError("max_buffer_size must be >= 0")
        state: MemoryChannelState[T] = MemoryChannelState(max_buffer_size)
        return (
            MemorySendChannel[T]._create(state),
            MemoryReceiveChannel[T]._create(state),
        )

    def __init__(self, max_buffer_size: int | float) -> None:  # noqa: PYI041
        ...


@attrs.frozen
class MemoryChannelStatistics:
    current_buffer_used: int
    max_buffer_size: int | float
    open_send_channels: int
    open_receive_channels: int
    tasks_waiting_send: int
    tasks_waiting_receive: int


@attrs.define
class MemoryChannelState(Generic[T]):
    max_buffer_size: int | float
    data: deque[T] = attrs.Factory(deque)
    # Counts of open endpoints using this state
    open_send_channels: int = 0
    open_receive_channels: int = 0
    # {task: value}
    send_tasks: OrderedDict[Task, T] = attrs.Factory(OrderedDict)
    # {task: None}
    receive_tasks: OrderedDict[Task, None] = attrs.Factory(OrderedDict)

    def statistics(self) -> MemoryChannelStatistics:
        return MemoryChannelStatistics(
            current_buffer_used=len(self.data),
            max_buffer_size=self.max_buffer_size,
            open_send_channels=self.open_send_channels,
            open_receive_channels=self.open_receive_channels,
            tasks_waiting_send=len(self.send_tasks),
            tasks_waiting_receive=len(self.receive_tasks),
        )


@final
@attrs.define(eq=False, repr=False, slots=False)
class MemorySendChannel(SendChannel[SendType], metaclass=NoPublicConstructor):
    _state: MemoryChannelState[SendType]
    _closed: bool = False
    # This is just the tasks waiting on *this* object. As compared to
    # self._state.send_tasks, which includes tasks from this object and
    # all clones.
    _tasks: set[Task] = attrs.Factory(set)

    def __attrs_post_init__(self) -> None:
        self._state.open_send_channels += 1

    def __repr__(self) -> str:
        return f"<send channel at {id(self):#x}, using buffer at {id(self._state):#x}>"

    def statistics(self) -> MemoryChannelStatistics:
        """Returns a `MemoryChannelStatistics` for the memory channel this is
        associated with."""
        # XX should we also report statistics specific to this object?
        return self._state.statistics()

    @enable_ki_protection
    def send_nowait(self, value: SendType) -> None:
        """Like `~trio.abc.SendChannel.send`, but if the channel's buffer is
        full, raises `WouldBlock` instead of blocking.

        """
        if self._closed:
            raise trio.ClosedResourceError
        if self._state.open_receive_channels == 0:
            raise trio.BrokenResourceError
        if self._state.receive_tasks:
            assert not self._state.data
            task, _ = self._state.receive_tasks.popitem(last=False)
            task.custom_sleep_data._tasks.remove(task)
            trio.lowlevel.reschedule(task, Value(value))
        elif len(self._state.data) < self._state.max_buffer_size:
            self._state.data.append(value)
        else:
            raise trio.WouldBlock

    @enable_ki_protection
    async def send(self, value: SendType) -> None:
        """See `SendChannel.send <trio.abc.SendChannel.send>`.

        Memory channels allow multiple tasks to call `send` at the same time.

        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            self.send_nowait(value)
        except trio.WouldBlock:
            pass
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()
            return

        task = trio.lowlevel.current_task()
        self._tasks.add(task)
        self._state.send_tasks[task] = value
        task.custom_sleep_data = self

        def abort_fn(_: RaiseCancelT) -> Abort:
            self._tasks.remove(task)
            del self._state.send_tasks[task]
            return trio.lowlevel.Abort.SUCCEEDED

        await trio.lowlevel.wait_task_rescheduled(abort_fn)

    # Return type must be stringified or use a TypeVar
    @enable_ki_protection
    def clone(self) -> MemorySendChannel[SendType]:
        """Clone this send channel object.

        This returns a new `MemorySendChannel` object, which acts as a
        duplicate of the original: sending on the new object does exactly the
        same thing as sending on the old object. (If you're familiar with
        `os.dup`, then this is a similar idea.)

        However, closing one of the objects does not close the other, and
        receivers don't get `EndOfChannel` until *all* clones have been
        closed.

        This is useful for communication patterns that involve multiple
        producers all sending objects to the same destination. If you give
        each producer its own clone of the `MemorySendChannel`, and then make
        sure to close each `MemorySendChannel` when it's finished, receivers
        will automatically get notified when all producers are finished. See
        :ref:`channel-mpmc` for examples.

        Raises:
          trio.ClosedResourceError: if you already closed this
              `MemorySendChannel` object.

        """
        if self._closed:
            raise trio.ClosedResourceError
        return MemorySendChannel._create(self._state)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @enable_ki_protection
    def close(self) -> None:
        """Close this send channel object synchronously.

        All channel objects have an asynchronous `~.AsyncResource.aclose` method.
        Memory channels can also be closed synchronously. This has the same
        effect on the channel and other tasks using it, but `close` is not a
        trio checkpoint. This simplifies cleaning up in cancelled tasks.

        Using ``with send_channel:`` will close the channel object on leaving
        the with block.

        """
        if self._closed:
            return
        self._closed = True
        for task in self._tasks:
            trio.lowlevel.reschedule(task, Error(trio.ClosedResourceError()))
            del self._state.send_tasks[task]
        self._tasks.clear()
        self._state.open_send_channels -= 1
        if self._state.open_send_channels == 0:
            assert not self._state.send_tasks
            for task in self._state.receive_tasks:
                task.custom_sleep_data._tasks.remove(task)
                trio.lowlevel.reschedule(task, Error(trio.EndOfChannel()))
            self._state.receive_tasks.clear()

    @enable_ki_protection
    async def aclose(self) -> None:
        """Close this send channel object asynchronously.

        See `MemorySendChannel.close`."""
        self.close()
        await trio.lowlevel.checkpoint()


@final
@attrs.define(eq=False, repr=False, slots=False)
class MemoryReceiveChannel(ReceiveChannel[ReceiveType], metaclass=NoPublicConstructor):
    _state: MemoryChannelState[ReceiveType]
    _closed: bool = False
    _tasks: set[trio._core._run.Task] = attrs.Factory(set)

    def __attrs_post_init__(self) -> None:
        self._state.open_receive_channels += 1

    def statistics(self) -> MemoryChannelStatistics:
        """Returns a `MemoryChannelStatistics` for the memory channel this is
        associated with."""
        return self._state.statistics()

    def __repr__(self) -> str:
        return (
            f"<receive channel at {id(self):#x}, using buffer at {id(self._state):#x}>"
        )

    @enable_ki_protection
    def receive_nowait(self) -> ReceiveType:
        """Like `~trio.abc.ReceiveChannel.receive`, but if there's nothing
        ready to receive, raises `WouldBlock` instead of blocking.

        """
        if self._closed:
            raise trio.ClosedResourceError
        if self._state.send_tasks:
            task, value = self._state.send_tasks.popitem(last=False)
            task.custom_sleep_data._tasks.remove(task)
            trio.lowlevel.reschedule(task)
            self._state.data.append(value)
            # Fall through
        if self._state.data:
            return self._state.data.popleft()
        if not self._state.open_send_channels:
            raise trio.EndOfChannel
        raise trio.WouldBlock

    @enable_ki_protection
    async def receive(self) -> ReceiveType:
        """See `ReceiveChannel.receive <trio.abc.ReceiveChannel.receive>`.

        Memory channels allow multiple tasks to call `receive` at the same
        time. The first task will get the first item sent, the second task
        will get the second item sent, and so on.

        """
        await trio.lowlevel.checkpoint_if_cancelled()
        try:
            value = self.receive_nowait()
        except trio.WouldBlock:
            pass
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()
            return value

        task = trio.lowlevel.current_task()
        self._tasks.add(task)
        self._state.receive_tasks[task] = None
        task.custom_sleep_data = self

        def abort_fn(_: RaiseCancelT) -> Abort:
            self._tasks.remove(task)
            del self._state.receive_tasks[task]
            return trio.lowlevel.Abort.SUCCEEDED

        # Not strictly guaranteed to return ReceiveType, but will do so unless
        # you intentionally reschedule with a bad value.
        return await trio.lowlevel.wait_task_rescheduled(abort_fn)  # type: ignore[no-any-return]

    @enable_ki_protection
    def clone(self) -> MemoryReceiveChannel[ReceiveType]:
        """Clone this receive channel object.

        This returns a new `MemoryReceiveChannel` object, which acts as a
        duplicate of the original: receiving on the new object does exactly
        the same thing as receiving on the old object.

        However, closing one of the objects does not close the other, and the
        underlying channel is not closed until all clones are closed. (If
        you're familiar with `os.dup`, then this is a similar idea.)

        This is useful for communication patterns that involve multiple
        consumers all receiving objects from the same underlying channel. See
        :ref:`channel-mpmc` for examples.

        .. warning:: The clones all share the same underlying channel.
           Whenever a clone :meth:`receive`\\s a value, it is removed from the
           channel and the other clones do *not* receive that value. If you
           want to send multiple copies of the same stream of values to
           multiple destinations, like :func:`itertools.tee`, then you need to
           find some other solution; this method does *not* do that.

        Raises:
          trio.ClosedResourceError: if you already closed this
              `MemoryReceiveChannel` object.

        """
        if self._closed:
            raise trio.ClosedResourceError
        return MemoryReceiveChannel._create(self._state)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @enable_ki_protection
    def close(self) -> None:
        """Close this receive channel object synchronously.

        All channel objects have an asynchronous `~.AsyncResource.aclose` method.
        Memory channels can also be closed synchronously. This has the same
        effect on the channel and other tasks using it, but `close` is not a
        trio checkpoint. This simplifies cleaning up in cancelled tasks.

        Using ``with receive_channel:`` will close the channel object on
        leaving the with block.

        """
        if self._closed:
            return
        self._closed = True
        for task in self._tasks:
            trio.lowlevel.reschedule(task, Error(trio.ClosedResourceError()))
            del self._state.receive_tasks[task]
        self._tasks.clear()
        self._state.open_receive_channels -= 1
        if self._state.open_receive_channels == 0:
            assert not self._state.receive_tasks
            for task in self._state.send_tasks:
                task.custom_sleep_data._tasks.remove(task)
                trio.lowlevel.reschedule(task, Error(trio.BrokenResourceError()))
            self._state.send_tasks.clear()
            self._state.data.clear()

    @enable_ki_protection
    async def aclose(self) -> None:
        """Close this receive channel object asynchronously.

        See `MemoryReceiveChannel.close`."""
        self.close()
        await trio.lowlevel.checkpoint()


class RecvChanWrapper(ReceiveChannel[T]):
    def __init__(
        self, recv_chan: MemoryReceiveChannel[T], send_semaphore: trio.Semaphore
    ) -> None:
        self._recv_chan = recv_chan
        self._send_semaphore = send_semaphore

    async def receive(self) -> T:
        self._send_semaphore.release()
        return await self._recv_chan.receive()

    async def aclose(self) -> None:
        await self._recv_chan.aclose()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._recv_chan.close()


def as_safe_channel(
    fn: Callable[P, AsyncGenerator[T, None]],
) -> Callable[P, AbstractAsyncContextManager[ReceiveChannel[T]]]:
    """Decorate an async generator function to make it cancellation-safe.

    The ``yield`` keyword offers a very convenient way to write iterators...
    which makes it really unfortunate that async generators are so difficult
    to call correctly.  Yielding from the inside of a cancel scope or a nursery
    to the outside `violates structured concurrency <https://xkcd.com/292/>`_
    with consequences explained in :pep:`789`.  Even then, resource cleanup
    errors remain common (:pep:`533`) unless you wrap every call in
    :func:`~contextlib.aclosing`.

    This decorator gives you the best of both worlds: with careful exception
    handling and a background task we preserve structured concurrency by
    offering only the safe interface, and you can still write your iterables
    with the convenience of ``yield``.  For example::

        @as_safe_channel
        async def my_async_iterable(arg, *, kwarg=True):
            while ...:
                item = await ...
                yield item

        async with my_async_iterable(...) as recv_chan:
            async for item in recv_chan:
                ...

    While the combined async-with-async-for can be inconvenient at first,
    the context manager is indispensable for both correctness and for prompt
    cleanup of resources.
    """
    # Perhaps a future PEP will adopt `async with for` syntax, like
    # https://coconut.readthedocs.io/en/master/DOCS.html#async-with-for

    @asynccontextmanager
    @wraps(fn)
    async def context_manager(
        *args: P.args, **kwargs: P.kwargs
    ) -> AsyncGenerator[trio._channel.RecvChanWrapper[T], None]:
        send_chan, recv_chan = trio.open_memory_channel[T](0)
        try:
            async with trio.open_nursery(strict_exception_groups=True) as nursery:
                agen = fn(*args, **kwargs)
                send_semaphore = trio.Semaphore(0)
                # `nursery.start` to make sure that we will clean up send_chan & agen
                # If this errors we don't close `recv_chan`, but the caller
                # never gets access to it, so that's not a problem.
                await nursery.start(
                    _move_elems_to_channel, agen, send_chan, send_semaphore
                )
                # `async with recv_chan` could eat exceptions, so use sync cm
                with RecvChanWrapper(recv_chan, send_semaphore) as wrapped_recv_chan:
                    yield wrapped_recv_chan
                # User has exited context manager, cancel to immediately close the
                # abandoned generator if it's still alive.
                nursery.cancel_scope.cancel(
                    "exited trio.as_safe_channel context manager"
                )
        except BaseExceptionGroup as eg:
            try:
                raise_single_exception_from_group(eg)
            except MultipleExceptionError:
                # In case user has except* we make it possible for them to handle the
                # exceptions.
                if sys.version_info >= (3, 11):
                    eg.add_note(
                        "Encountered exception during cleanup of generator object, as "
                        "well as exception in the contextmanager body - unable to unwrap."
                    )

                raise eg from None

    async def _move_elems_to_channel(
        agen: AsyncGenerator[T, None],
        send_chan: trio.MemorySendChannel[T],
        send_semaphore: trio.Semaphore,
        task_status: trio.TaskStatus,
    ) -> None:
        # `async with send_chan` will eat exceptions,
        # see https://github.com/python-trio/trio/issues/1559
        with send_chan:
            # replace try-finally with contextlib.aclosing once python39 is
            # dropped:
            try:
                task_status.started()
                while True:
                    # wait for receiver to call next on the aiter
                    await send_semaphore.acquire()
                    if not send_chan._state.open_receive_channels:
                        # skip the possibly-expensive computation in the generator,
                        # if we know it will be impossible to send the result.
                        break
                    try:
                        value = await agen.__anext__()
                    except StopAsyncIteration:
                        return
                    # Send the value to the channel
                    try:
                        await send_chan.send(value)
                    except BrokenResourceError:
                        break  # closed since we checked above
            finally:
                # work around `.aclose()` not suppressing GeneratorExit in an
                # ExceptionGroup:
                # TODO: make an issue on CPython about this
                try:
                    await agen.aclose()
                except BaseExceptionGroup as exceptions:
                    removed, narrowed_exceptions = exceptions.split(GeneratorExit)

                    # TODO: extract a helper to flatten exception groups
                    removed_exceptions: list[BaseException | None] = [removed]
                    genexits_seen = 0
                    for e in removed_exceptions:
                        if isinstance(e, BaseExceptionGroup):
                            removed_exceptions.extend(e.exceptions)  # noqa: B909
                        else:
                            genexits_seen += 1

                    if genexits_seen > 1:
                        exc = AssertionError("More than one GeneratorExit found.")
                        if narrowed_exceptions is None:
                            narrowed_exceptions = exceptions.derive([exc])
                        else:
                            narrowed_exceptions = narrowed_exceptions.derive(
                                [*narrowed_exceptions.exceptions, exc]
                            )
                    if narrowed_exceptions is not None:
                        raise narrowed_exceptions from None

    return context_manager
