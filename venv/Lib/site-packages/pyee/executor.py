# -*- coding: utf-8 -*-

from concurrent.futures import Executor, Future, ThreadPoolExecutor
from types import TracebackType
from typing import Any, Callable, Dict, Optional, Tuple, Type

from pyee.base import EventEmitter

Self = Any

__all__ = ["ExecutorEventEmitter"]


class ExecutorEventEmitter(EventEmitter):
    """An event emitter class which runs handlers in a `concurrent.futures`
    executor.

    By default, this class creates a default `ThreadPoolExecutor`, but
    a custom executor may also be passed in explicitly to, for instance,
    use a `ProcessPoolExecutor` instead.

    This class runs all emitted events on the configured executor. Errors
    captured by the resulting Future are automatically emitted on the
    `error` event. This is unlike the EventEmitter, which have no error
    handling.

    The underlying executor may be shut down by calling the `shutdown`
    method. Alternately you can treat the event emitter as a context manager:

    ```py
    with ExecutorEventEmitter() as ee:
        # Underlying executor open

        @ee.on('data')
        def handler(data):
            print(data)

        ee.emit('event')

    # Underlying executor closed
    ```

    Since the function call is scheduled on an executor, emit is always
    non-blocking.

    No effort is made to ensure thread safety, beyond using an executor.
    """

    def __init__(self: Self, executor: Optional[Executor] = None) -> None:
        super(ExecutorEventEmitter, self).__init__()
        if executor:
            self._executor: Executor = executor
        else:
            self._executor = ThreadPoolExecutor()

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        future: Future = self._executor.submit(f, *args, **kwargs)

        @future.add_done_callback
        def _callback(f: Future) -> None:
            exc: Optional[BaseException] = f.exception()
            if isinstance(exc, Exception):
                self.emit("error", exc)
            elif exc is not None:
                raise exc

    def shutdown(self: Self, wait: bool = True) -> None:
        """Call `shutdown` on the internal executor."""

        self._executor.shutdown(wait=wait)

    def __enter__(self: Self) -> "ExecutorEventEmitter":
        return self

    def __exit__(
        self: Self, type: Type[Exception], value: Exception, traceback: TracebackType
    ) -> Optional[bool]:
        self.shutdown()
        return None
