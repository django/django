# -*- coding: utf-8 -*-

from contextlib import AbstractAsyncContextManager, asynccontextmanager
from types import TracebackType
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    cast,
    Dict,
    Optional,
    Tuple,
    Type,
)

import trio

from pyee.base import EventEmitter, PyeeError

Self = Any

__all__ = ["TrioEventEmitter"]


Nursery = trio.Nursery


class TrioEventEmitter(EventEmitter):
    """An event emitter class which can run trio tasks in a trio nursery.

    By default, this class will lazily create both a nursery manager (the
    object returned from `trio.open_nursery()` and a nursery (the object
    yielded by using the nursery manager as an async context manager). It is
    also possible to supply an existing nursery manager via the `manager`
    argument, or an existing nursery via the `nursery` argument.

    Instances of TrioEventEmitter are themselves async context managers, so
    that they may manage the lifecycle of the underlying trio nursery. For
    example, typical usage of this library may look something like this::

    ```py
    async with TrioEventEmitter() as ee:
        # Underlying nursery is instantiated and ready to go
        @ee.on('data')
        async def handler(data):
            print(data)

        ee.emit('event')

    # Underlying nursery and manager have been cleaned up
    ```

    Unlike the case with the EventEmitter, all exceptions raised by event
    handlers are automatically emitted on the `error` event. This is
    important for trio coroutines specifically but is also handled for
    synchronous functions for consistency.

    For trio coroutine event handlers, calling emit is non-blocking. In other
    words, you should not attempt to await emit; the coroutine is scheduled
    in a fire-and-forget fashion.
    """

    def __init__(
        self: Self,
        nursery: Optional[Nursery] = None,
        manager: Optional["AbstractAsyncContextManager[trio.Nursery]"] = None,
    ):
        super(TrioEventEmitter, self).__init__()
        self._nursery: Optional[Nursery] = None
        self._manager: Optional["AbstractAsyncContextManager[trio.Nursery]"] = None
        if nursery:
            if manager:
                raise PyeeError(
                    "You may either pass a nursery or a nursery manager " "but not both"
                )
            self._nursery = nursery
        elif manager:
            self._manager = manager
        else:
            self._manager = trio.open_nursery()

    def _async_runner(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> Callable[[], Awaitable[None]]:
        async def runner() -> None:
            try:
                await f(*args, **kwargs)
            except Exception as exc:
                self.emit("error", exc)

        return runner

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        if not self._nursery:
            raise PyeeError("Uninitialized trio nursery")
        self._nursery.start_soon(self._async_runner(f, args, kwargs))

    @asynccontextmanager
    async def context(
        self: Self,
    ) -> AsyncGenerator["TrioEventEmitter", None]:
        """Returns an async contextmanager which manages the underlying
        nursery to the EventEmitter. The `TrioEventEmitter`'s
        async context management methods are implemented using this
        function, but it may also be used directly for clarity.
        """
        if self._nursery is not None:
            yield self
        elif self._manager is not None:
            async with self._manager as nursery:
                self._nursery = nursery
                yield self
        else:
            raise PyeeError("Uninitialized nursery or nursery manager")

    async def __aenter__(self: Self) -> "TrioEventEmitter":
        self._context: Optional[AbstractAsyncContextManager["TrioEventEmitter"]] = (
            self.context()
        )
        return await cast(Any, self._context).__aenter__()

    async def __aexit__(
        self: Self,
        type: Optional[Type[BaseException]],
        value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        if self._context is None:
            raise PyeeError("Attempting to exit uninitialized context")
        rv = await self._context.__aexit__(type, value, traceback)
        self._context = None
        self._nursery = None
        self._manager = None
        return rv
