# -*- coding: utf-8 -*-

from collections import OrderedDict
from threading import Lock
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    overload,
    Set,
    Tuple,
    TypeVar,
    Union,
)

Self = Any


class PyeeException(Exception):
    """An exception internal to pyee. Deprecated in favor of PyeeError."""


class PyeeError(PyeeException):
    """An error internal to pyee."""


Handler = TypeVar("Handler", bound=Callable)


class EventEmitter:
    """The base event emitter class. All other event emitters inherit from
    this class.

    Most events are registered with an emitter via the `on` and `once`
    methods, and fired with the `emit` method. However, pyee event emitters
    have two *special* events:

    - `new_listener`: Fires whenever a new listener is created. Listeners for
      this event do not fire upon their own creation.

    - `error`: When emitted raises an Exception by default, behavior can be
      overridden by attaching callback to the event.

      For example:

    ```py
    @ee.on('error')
    def on_error(message):
        logging.err(message)

    ee.emit('error', Exception('something blew up'))
    ```

    All callbacks are handled in a synchronous, blocking manner. As in node.js,
    raised exceptions are not automatically handled for you---you must catch
    your own exceptions, and treat them accordingly.
    """

    def __init__(self: Self) -> None:
        self._events: Dict[
            str,
            "OrderedDict[Callable, Callable]",
        ] = dict()
        self._lock: Lock = Lock()

    def __getstate__(self: Self) -> Mapping[str, Any]:
        state = self.__dict__.copy()
        del state["_lock"]
        return state

    def __setstate__(self: Self, state: Mapping[str, Any]) -> None:
        self.__dict__.update(state)
        self._lock = Lock()

    @overload
    def on(self: Self, event: str) -> Callable[[Handler], Handler]: ...
    @overload
    def on(self: Self, event: str, f: Handler) -> Handler: ...

    def on(
        self: Self, event: str, f: Optional[Handler] = None
    ) -> Union[Handler, Callable[[Handler], Handler]]:
        """Registers the function `f` to the event name `event`, if provided.

        If `f` isn't provided, this method calls `EventEmitter#listens_to`, and
        otherwise calls `EventEmitter#add_listener`. In other words, you may either
        use it as a decorator:

        ```py
        @ee.on('data')
        def data_handler(data):
            print(data)
        ```

        Or directly:

        ```py
        ee.on('data', data_handler)
        ```

        In both the decorated and undecorated forms, the event handler is
        returned. The upshot of this is that you can call decorated handlers
        directly, as well as use them in remove_listener calls.

        Note that this method's return type is a union type. If you are using
        mypy or pyright, you will probably want to use either
        `EventEmitter#listens_to` or `EventEmitter#add_listener`.
        """
        if f is None:
            return self.listens_to(event)
        else:
            return self.add_listener(event, f)

    def listens_to(self: Self, event: str) -> Callable[[Handler], Handler]:
        """Returns a decorator which will register the decorated function to
        the event name `event`:

        ```py
        @ee.listens_to("event")
        def data_handler(data):
            print(data)
        ```

        By only supporting the decorator use case, this method has improved
        type safety over `EventEmitter#on`.
        """

        def on(f: Handler) -> Handler:
            self._add_event_handler(event, f, f)
            return f

        return on

    def add_listener(self: Self, event: str, f: Handler) -> Handler:
        """Register the function `f` to the event name `event`:

        ```
        def data_handler(data):
            print(data)

        h = ee.add_listener("event", data_handler)
        ```

        By not supporting the decorator use case, this method has improved
        type safety over `EventEmitter#on`.
        """
        self._add_event_handler(event, f, f)
        return f

    def _add_event_handler(self: Self, event: str, k: Callable, v: Callable):
        # Fire 'new_listener' *before* adding the new listener!
        self.emit("new_listener", event, k)

        # Add the necessary function
        # Note that k and v are the same for `on` handlers, but
        # different for `once` handlers, where v is a wrapped version
        # of k which removes itself before calling k
        with self._lock:
            if event not in self._events:
                self._events[event] = OrderedDict()
            self._events[event][k] = v

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        f(*args, **kwargs)

    def event_names(self: Self) -> Set[str]:
        """Get a set of events that this emitter is listening to."""
        return set(self._events.keys())

    def _emit_handle_potential_error(self: Self, event: str, error: Any) -> None:
        if event == "error":
            if isinstance(error, Exception):
                raise error
            else:
                raise PyeeError(f"Uncaught, unspecified 'error' event: {error}")

    def _call_handlers(
        self: Self,
        event: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> bool:
        handled = False

        with self._lock:
            funcs = list(self._events.get(event, OrderedDict()).values())
        for f in funcs:
            self._emit_run(f, args, kwargs)
            handled = True

        return handled

    def emit(
        self: Self,
        event: str,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit `event`, passing `*args` and `**kwargs` to each attached
        function. Returns `True` if any functions are attached to `event`;
        otherwise returns `False`.

        Example:

        ```py
        ee.emit('data', '00101001')
        ```

        Assuming `data` is an attached function, this will call
        `data('00101001')'`.
        """
        handled = self._call_handlers(event, args, kwargs)

        if not handled:
            self._emit_handle_potential_error(event, args[0] if args else None)

        return handled

    def once(
        self: Self,
        event: str,
        f: Optional[Callable] = None,
    ) -> Callable:
        """The same as `ee.on`, except that the listener is automatically
        removed after being called.
        """

        def _wrapper(f: Callable) -> Callable:
            def g(
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                with self._lock:
                    # Check that the event wasn't removed already right
                    # before the lock
                    if event in self._events and f in self._events[event]:
                        self._remove_listener(event, f)
                    else:
                        return None
                # f may return a coroutine, so we need to return that
                # result here so that emit can schedule it
                return f(*args, **kwargs)

            self._add_event_handler(event, f, g)
            return f

        if f is None:
            return _wrapper
        else:
            return _wrapper(f)

    def _remove_listener(self: Self, event: str, f: Callable) -> None:
        """Naked unprotected removal."""
        if event in self._events:
            self._events[event].pop(f)
            if not self._events[event]:
                del self._events[event]

    def remove_listener(self: Self, event: str, f: Callable) -> None:
        """Removes the function `f` from `event`."""
        with self._lock:
            self._remove_listener(event, f)

    def remove_all_listeners(self: Self, event: Optional[str] = None) -> None:
        """Remove all listeners attached to `event`.
        If `event` is `None`, remove all listeners on all events.
        """
        with self._lock:
            if event is not None:
                self._events[event] = OrderedDict()
            else:
                self._events = dict()

    def listeners(self: Self, event: str) -> List[Callable]:
        """Returns a list of all listeners registered to the `event`."""
        return list(self._events.get(event, OrderedDict()).keys())
