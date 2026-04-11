# -*- coding: utf-8 -*-

from asyncio import AbstractEventLoop, ensure_future, Future, iscoroutine, wait
from typing import Any, Callable, cast, Dict, Optional, Set, Tuple

from pyee.base import EventEmitter

Self = Any

__all__ = ["AsyncIOEventEmitter"]


class AsyncIOEventEmitter(EventEmitter):
    """An event emitter class which can run asyncio coroutines in addition to
    synchronous blocking functions. For example:

    ```py
    @ee.on('event')
    async def async_handler(*args, **kwargs):
        await returns_a_future()
    ```

    On emit, the event emitter  will automatically schedule the coroutine using
    `asyncio.ensure_future` and the configured event loop (defaults to
    `asyncio.get_event_loop()`).

    Unlike the case with the EventEmitter, all exceptions raised by
    event handlers are automatically emitted on the `error` event. This is
    important for asyncio coroutines specifically but is also handled for
    synchronous functions for consistency.

    When `loop` is specified, the supplied event loop will be used when
    scheduling work with `ensure_future`. Otherwise, the default asyncio
    event loop is used.

    For asyncio coroutine event handlers, calling emit is non-blocking.
    In other words, you do not have to await any results from emit, and the
    coroutine is scheduled in a fire-and-forget fashion.
    """

    def __init__(self: Self, loop: Optional[AbstractEventLoop] = None) -> None:
        super(AsyncIOEventEmitter, self).__init__()
        self._loop: Optional[AbstractEventLoop] = loop
        self._waiting: Set[Future] = set()

    def emit(
        self: Self,
        event: str,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit `event`, passing `*args` and `**kwargs` to each attached
        function or coroutine. Returns `True` if any functions are attached to
        `event`; otherwise returns `False`.

        Example:

        ```py
        ee.emit('data', '00101001')
        ```

        Assuming `data` is an attached function, this will call
        `data('00101001')'`.

        When executing coroutine handlers, their respective futures will be
        stored in a "waiting" state. These futures may be waited on or
        canceled with `wait_for_complete` and `cancel`, respectively; and
        their status may be checked via the `complete` property.
        """
        return super().emit(event, *args, **kwargs)

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        try:
            coro: Any = f(*args, **kwargs)
        except Exception as exc:
            self.emit("error", exc)
        else:
            if iscoroutine(coro):
                if self._loop:
                    # ensure_future is *extremely* cranky about the types here,
                    # but this is relatively well-tested and I think the types
                    # are more strict than they should be
                    fut: Any = ensure_future(cast(Any, coro), loop=self._loop)
                else:
                    fut = ensure_future(cast(Any, coro))

            elif isinstance(coro, Future):
                fut = cast(Any, coro)
            else:
                return

            def callback(f: Future) -> None:
                self._waiting.discard(f)

                if f.cancelled():
                    return

                exc: Optional[BaseException] = f.exception()
                if exc:
                    self.emit("error", exc)

            fut.add_done_callback(callback)
            self._waiting.add(fut)

    async def wait_for_complete(self: Self) -> None:
        """Waits for all pending tasks to complete. For example:

        ```py
        @ee.on('event')
        async def async_handler(*args, **kwargs):
            await returns_a_future()

        # Triggers execution of async_handler
        ee.emit('data', '00101001')

        await ee.wait_for_complete()

        # async_handler has completed execution
        ```

        This is useful if you're attempting a graceful shutdown of your
        application and want to ensure all coroutines have completed execution
        beforehand.
        """
        if self._waiting:
            await wait(self._waiting)

    def cancel(self: Self) -> None:
        """Cancel all pending tasks. For example:

        ```py
        @ee.on('event')
        async def async_handler(*args, **kwargs):
            await returns_a_future()

        # Triggers execution of async_handler
        ee.emit('data', '00101001')

        ee.cancel()

        # async_handler execution has been canceled
        ```

        This is useful if you're attempting to shut down your application and
        attempts at a graceful shutdown via `wait_for_complete` have failed.
        """
        for fut in self._waiting:
            if not fut.done() and not fut.cancelled():
                fut.cancel()
        self._waiting.clear()

    @property
    def complete(self: Self) -> bool:
        """When true, there are no pending tasks, and execution is complete.
        For example:

        ```py
        @ee.on('event')
        async def async_handler(*args, **kwargs):
            await returns_a_future()

        # Triggers execution of async_handler
        ee.emit('data', '00101001')

        # async_handler is still running, so this prints False
        print(ee.complete)

        await ee.wait_for_complete()

        # async_handler has completed execution, so this prints True
        print(ee.complete)
        ```
        """
        return not self._waiting
