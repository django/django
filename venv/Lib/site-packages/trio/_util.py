# Little utilities we use internally
from __future__ import annotations

import collections.abc
import inspect
import signal
from abc import ABCMeta
from collections.abc import Awaitable, Callable, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    NoReturn,
    TypeVar,
    final as std_final,
)

from sniffio import thread_local as sniffio_loop

import trio

# Explicit "Any" is not allowed
CallT = TypeVar("CallT", bound=Callable[..., Any])  # type: ignore[explicit-any]
T = TypeVar("T")
RetT = TypeVar("RetT")

if TYPE_CHECKING:
    import sys
    from types import AsyncGeneratorType, TracebackType

    from typing_extensions import TypeVarTuple, Unpack

    if sys.version_info < (3, 11):
        from exceptiongroup import BaseExceptionGroup

    PosArgsT = TypeVarTuple("PosArgsT")


# See: #461 as to why this is needed.
# The gist is that threading.main_thread() has the capability to lie to us
# if somebody else edits the threading ident cache to replace the main
# thread; causing threading.current_thread() to return a _DummyThread,
# causing the C-c check to fail, and so on.
# Trying to use signal out of the main thread will fail, so we can then
# reliably check if this is the main thread without relying on a
# potentially modified threading.
def is_main_thread() -> bool:
    """Attempt to reliably check if we are in the main thread."""
    try:
        signal.signal(signal.SIGINT, signal.getsignal(signal.SIGINT))
        return True
    except (TypeError, ValueError):
        return False


######
# Call the function and get the coroutine object, while giving helpful
# errors for common mistakes. Returns coroutine object.
######
def coroutine_or_error(
    async_fn: Callable[[Unpack[PosArgsT]], Awaitable[RetT]],
    *args: Unpack[PosArgsT],
) -> collections.abc.Coroutine[object, NoReturn, RetT]:
    def _return_value_looks_like_wrong_library(value: object) -> bool:
        # Returned by legacy @asyncio.coroutine functions, which includes
        # a surprising proportion of asyncio builtins.
        if isinstance(value, collections.abc.Generator):
            return True
        # The protocol for detecting an asyncio Future-like object
        if getattr(value, "_asyncio_future_blocking", None) is not None:
            return True
        # This janky check catches tornado Futures and twisted Deferreds.
        # By the time we're calling this function, we already know
        # something has gone wrong, so a heuristic is pretty safe.
        return value.__class__.__name__ in ("Future", "Deferred")

    # Make sure a sync-fn-that-returns-coroutine still sees itself as being
    # in trio context
    prev_loop, sniffio_loop.name = sniffio_loop.name, "trio"

    try:
        coro = async_fn(*args)

    except TypeError:
        # Give good error for: nursery.start_soon(trio.sleep(1))
        if isinstance(async_fn, collections.abc.Coroutine):
            # explicitly close coroutine to avoid RuntimeWarning
            async_fn.close()

            raise TypeError(
                "Trio was expecting an async function, but instead it got "
                f"a coroutine object {async_fn!r}\n"
                "\n"
                "Probably you did something like:\n"
                "\n"
                f"  trio.run({async_fn.__name__}(...))            # incorrect!\n"
                f"  nursery.start_soon({async_fn.__name__}(...))  # incorrect!\n"
                "\n"
                "Instead, you want (notice the parentheses!):\n"
                "\n"
                f"  trio.run({async_fn.__name__}, ...)            # correct!\n"
                f"  nursery.start_soon({async_fn.__name__}, ...)  # correct!",
            ) from None

        # Give good error for: nursery.start_soon(future)
        if _return_value_looks_like_wrong_library(async_fn):
            raise TypeError(
                "Trio was expecting an async function, but instead it got "
                f"{async_fn!r} – are you trying to use a library written for "
                "asyncio/twisted/tornado or similar? That won't work "
                "without some sort of compatibility shim.",
            ) from None

        raise

    finally:
        sniffio_loop.name = prev_loop

    # We can't check iscoroutinefunction(async_fn), because that will fail
    # for things like functools.partial objects wrapping an async
    # function. So we have to just call it and then check whether the
    # return value is a coroutine object.
    # Note: will not be necessary on python>=3.8, see https://bugs.python.org/issue34890
    # TODO: python3.7 support is now dropped, so the above can be addressed.
    if not isinstance(coro, collections.abc.Coroutine):
        # Give good error for: nursery.start_soon(func_returning_future)
        if _return_value_looks_like_wrong_library(coro):
            raise TypeError(
                f"Trio got unexpected {coro!r} – are you trying to use a "
                "library written for asyncio/twisted/tornado or similar? "
                "That won't work without some sort of compatibility shim.",
            )

        if inspect.isasyncgen(coro):
            raise TypeError(
                "start_soon expected an async function but got an async "
                f"generator {coro!r}",
            )

        # Give good error for: nursery.start_soon(some_sync_fn)
        raise TypeError(
            "Trio expected an async function, but {!r} appears to be "
            "synchronous".format(getattr(async_fn, "__qualname__", async_fn)),
        )

    return coro


class ConflictDetector:
    """Detect when two tasks are about to perform operations that would
    conflict.

    Use as a synchronous context manager; if two tasks enter it at the same
    time then the second one raises an error. You can use it when there are
    two pieces of code that *would* collide and need a lock if they ever were
    called at the same time, but that should never happen.

    We use this in particular for things like, making sure that two different
    tasks don't call sendall simultaneously on the same stream.

    """

    def __init__(self, msg: str) -> None:
        self._msg = msg
        self._held = False

    def __enter__(self) -> None:
        if self._held:
            raise trio.BusyResourceError(self._msg)
        else:
            self._held = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._held = False


def async_wraps(  # type: ignore[explicit-any]
    cls: type[object],
    wrapped_cls: type[object],
    attr_name: str,
) -> Callable[[CallT], CallT]:
    """Similar to wraps, but for async wrappers of non-async functions."""

    def decorator(func: CallT) -> CallT:  # type: ignore[explicit-any]
        func.__name__ = attr_name
        func.__qualname__ = f"{cls.__qualname__}.{attr_name}"

        func.__doc__ = f"Like :meth:`~{wrapped_cls.__module__}.{wrapped_cls.__qualname__}.{attr_name}`, but async."

        return func

    return decorator


def fixup_module_metadata(
    module_name: str,
    namespace: collections.abc.Mapping[str, object],
) -> None:
    seen_ids: set[int] = set()

    def fix_one(qualname: str, name: str, obj: object) -> None:
        # avoid infinite recursion (relevant when using
        # typing.Generic, for example)
        if id(obj) in seen_ids:
            return
        seen_ids.add(id(obj))

        mod = getattr(obj, "__module__", None)
        if mod is not None and mod.startswith("trio."):
            obj.__module__ = module_name
            # Modules, unlike everything else in Python, put fully-qualified
            # names into their __name__ attribute. We check for "." to avoid
            # rewriting these.
            if hasattr(obj, "__name__") and "." not in obj.__name__:
                obj.__name__ = name
                if hasattr(obj, "__qualname__"):
                    obj.__qualname__ = qualname
            if isinstance(obj, type):
                for attr_name, attr_value in obj.__dict__.items():
                    fix_one(objname + "." + attr_name, attr_name, attr_value)

    for objname, obj in namespace.items():
        if not objname.startswith("_"):  # ignore private attributes
            fix_one(objname, objname, obj)


def _init_final_cls(cls: type[object]) -> NoReturn:
    """Raises an exception when a final class is subclassed."""
    raise TypeError(f"{cls.__module__}.{cls.__qualname__} does not support subclassing")


def _final_impl(decorated: type[T]) -> type[T]:
    """Decorator that enforces a class to be final (i.e., subclass not allowed).

    If a class uses this metaclass like this::

        @final
        class SomeClass:
            pass

    The metaclass will ensure that no subclass can be created.

    Raises
    ------
    - TypeError if a subclass is created
    """
    # Override the method blindly. We're always going to raise, so it doesn't
    # matter what the original did (if anything).
    decorated.__init_subclass__ = classmethod(_init_final_cls)  # type: ignore[assignment]
    # Apply the typing decorator, in 3.11+ it adds a __final__ marker attribute.
    return std_final(decorated)


if TYPE_CHECKING:
    from typing import final
else:
    final = _final_impl


@final  # No subclassing of NoPublicConstructor itself.
class NoPublicConstructor(ABCMeta):
    """Metaclass that ensures a private constructor.

    If a class uses this metaclass like this::

        @final
        class SomeClass(metaclass=NoPublicConstructor):
            pass

    The metaclass will ensure that no instance can be initialized. This should always be
    used with @final.

    If you try to instantiate your class (SomeClass()), a TypeError will be thrown. Use
    _create() instead in the class's implementation.

    Raises
    ------
    - TypeError if an instance is created.
    """

    def __call__(cls, *args: object, **kwargs: object) -> None:
        raise TypeError(
            f"{cls.__module__}.{cls.__qualname__} has no public constructor",
        )

    def _create(cls: type[T], *args: object, **kwargs: object) -> T:
        return super().__call__(*args, **kwargs)  # type: ignore


def name_asyncgen(agen: AsyncGeneratorType[object, NoReturn]) -> str:
    """Return the fully-qualified name of the async generator function
    that produced the async generator iterator *agen*.
    """
    if not hasattr(agen, "ag_code"):  # pragma: no cover
        return repr(agen)
    try:
        module = agen.ag_frame.f_globals["__name__"]
    except (AttributeError, KeyError):
        module = f"<{agen.ag_code.co_filename}>"
    try:
        qualname = agen.__qualname__
    except AttributeError:
        qualname = agen.ag_code.co_name
    return f"{module}.{qualname}"


# work around a pyright error
if TYPE_CHECKING:
    Fn = TypeVar("Fn", bound=Callable[..., object])  # type: ignore[explicit-any]

    def wraps(  # type: ignore[explicit-any]
        wrapped: Callable[..., object],
        assigned: Sequence[str] = ...,
        updated: Sequence[str] = ...,
    ) -> Callable[[Fn], Fn]: ...

else:
    from functools import wraps  # noqa: F401  # this is re-exported


def raise_saving_context(exc: BaseException) -> NoReturn:
    """This helper allows re-raising an exception without __context__ being set."""
    # cause does not need special handling, we simply avoid using `raise .. from ..`
    # __suppress_context__ also does not need handling, it's only set if modifying cause
    __tracebackhide__ = True
    context = exc.__context__
    try:
        raise exc
    finally:
        exc.__context__ = context
        del exc, context


class MultipleExceptionError(Exception):
    """Raised by raise_single_exception_from_group if encountering multiple
    non-cancelled exceptions."""


def raise_single_exception_from_group(
    eg: BaseExceptionGroup[BaseException],
) -> NoReturn:
    """This function takes an exception group that is assumed to have at most
    one non-cancelled exception, which it reraises as a standalone exception.

    This exception may be an exceptiongroup itself, in which case it will not be unwrapped.

    If a :exc:`KeyboardInterrupt` is encountered, a new KeyboardInterrupt is immediately
    raised with the entire group as cause.

    If the group only contains :exc:`Cancelled` it reraises the first one encountered.

    It will retain context and cause of the contained exception, and entirely discard
    the cause/context of the group(s).

    If multiple non-cancelled exceptions are encountered, it raises
    :exc:`AssertionError`.
    """
    # immediately bail out if there's any KI or SystemExit
    for e in eg.exceptions:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise type(e)(*e.args) from eg

    cancelled_exception: trio.Cancelled | None = None
    noncancelled_exception: BaseException | None = None

    for e in eg.exceptions:
        if isinstance(e, trio.Cancelled):
            if cancelled_exception is None:
                cancelled_exception = e
        elif noncancelled_exception is None:
            noncancelled_exception = e
        else:
            raise MultipleExceptionError(
                "Attempted to unwrap exceptiongroup with multiple non-cancelled exceptions. This is often caused by a bug in the caller."
            ) from eg

    if noncancelled_exception is not None:
        raise_saving_context(noncancelled_exception)

    assert cancelled_exception is not None, "group can't be empty"
    raise_saving_context(cancelled_exception)
