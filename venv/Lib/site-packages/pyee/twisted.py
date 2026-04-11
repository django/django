# -*- coding: utf-8 -*-

from asyncio import iscoroutine
from typing import Any, Callable, cast, Dict, Optional, Tuple

from twisted.internet.defer import Deferred, ensureDeferred
from twisted.python.failure import Failure

from pyee.base import EventEmitter, PyeeError

Self = Any


__all__ = ["TwistedEventEmitter"]


class TwistedEventEmitter(EventEmitter):
    """An event emitter class which can run twisted coroutines and handle
    returned Deferreds, in addition to synchronous blocking functions. For
    example:

    ```py
    @ee.on('event')
    @inlineCallbacks
    def async_handler(*args, **kwargs):
        yield returns_a_deferred()
    ```

    or:

    ```py
    @ee.on('event')
    async def async_handler(*args, **kwargs):
        await returns_a_deferred()
    ```


    When async handlers fail, Failures are first emitted on the `failure`
    event. If there are no `failure` handlers, the Failure's associated
    exception is then emitted on the `error` event. If there are no `error`
    handlers, the exception is raised. For consistency, when handlers raise
    errors synchronously, they're captured, wrapped in a Failure and treated
    as an async failure. This is unlike the behavior of EventEmitter,
    which have no special error handling.

    For twisted coroutine event handlers, calling emit is non-blocking.
    In other words, you do not have to await any results from emit, and the
    coroutine is scheduled in a fire-and-forget fashion.

    Similar behavior occurs for "sync" functions which return Deferreds.
    """

    def __init__(self: Self) -> None:
        super(TwistedEventEmitter, self).__init__()

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        d: Optional[Deferred[Any]] = None
        try:
            result = f(*args, **kwargs)
        except Exception:
            self.emit("failure", Failure())
        else:
            if iscoroutine(result):
                d = ensureDeferred(result)
            elif isinstance(result, Deferred):
                d = result
            elif not d:
                return

            def errback(failure: Failure) -> None:
                if failure:
                    self.emit("failure", failure)

            d.addErrback(errback)

    def _emit_handle_potential_error(self: Self, event: str, error: Any) -> None:
        if event == "failure":
            if isinstance(error, Failure):
                try:
                    error.raiseException()
                except Exception as exc:
                    self.emit("error", exc)
            elif isinstance(error, Exception):
                self.emit("error", error)
            else:
                self.emit("error", PyeeError(f"Unexpected failure object: {error}"))
        else:
            cast(Any, super(TwistedEventEmitter, self))._emit_handle_potential_error(
                event, error
            )
