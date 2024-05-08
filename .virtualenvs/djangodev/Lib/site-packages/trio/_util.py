# Little utilities we use internally
from __future__ import annotations

import collections.abc
import inspect
import os
import signal
import threading
from abc import ABCMeta
from functools import update_wrapper
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    NoReturn,
    Sequence,
    TypeVar,
    final as std_final,
)

from sniffio import thread_local as sniffio_loop

import trio

CallT = TypeVar("CallT", bound=Callable[..., Any])
T = TypeVar("T")
RetT = TypeVar("RetT")

if TYPE_CHECKING:
    from types import AsyncGeneratorType, TracebackType

    from typing_extensions import ParamSpec, Self, TypeVarTuple, Unpack

    ArgsT = ParamSpec("ArgsT")
    PosArgsT = TypeVarTuple("PosArgsT")


if TYPE_CHECKING:
    # Don't type check the implementation below, pthread_kill does not exist on Windows.
    def signal_raise(signum: int) -> None: ...


# Equivalent to the C function raise(), which Python doesn't wrap
elif os.name == "nt":
    # On Windows, os.kill exists but is really weird.
    #
    # If you give it CTRL_C_EVENT or CTRL_BREAK_EVENT, it tries to deliver
    # those using GenerateConsoleCtrlEvent. But I found that when I tried
    # to run my test normally, it would freeze waiting... unless I added
    # print statements, in which case the test suddenly worked. So I guess
    # these signals are only delivered if/when you access the console? I
    # don't really know what was going on there. From reading the
    # GenerateConsoleCtrlEvent docs I don't know how it worked at all.
    #
    # I later spent a bunch of time trying to make GenerateConsoleCtrlEvent
    # work for creating synthetic control-C events, and... failed
    # utterly. There are lots of details in the code and comments
    # removed/added at this commit:
    #     https://github.com/python-trio/trio/commit/95843654173e3e826c34d70a90b369ba6edf2c23
    #
    # OTOH, if you pass os.kill any *other* signal number... then CPython
    # just calls TerminateProcess (wtf).
    #
    # So, anyway, os.kill is not so useful for testing purposes. Instead,
    # we use raise():
    #
    #   https://msdn.microsoft.com/en-us/library/dwwzkt4c.aspx
    #
    # Have to import cffi inside the 'if os.name' block because we don't
    # depend on cffi on non-Windows platforms. (It would be easy to switch
    # this to ctypes though if we ever remove the cffi dependency.)
    #
    # Some more information:
    #   https://bugs.python.org/issue26350
    #
    # Anyway, we use this for two things:
    # - redelivering unhandled signals
    # - generating synthetic signals for tests
    # and for both of those purposes, 'raise' works fine.
    import cffi

    _ffi = cffi.FFI()
    _ffi.cdef("int raise(int);")
    _lib = _ffi.dlopen("api-ms-win-crt-runtime-l1-1-0.dll")
    signal_raise = getattr(_lib, "raise")
else:

    def signal_raise(signum: int) -> None:
        signal.pthread_kill(threading.get_ident(), signum)


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
        if value.__class__.__name__ in ("Future", "Deferred"):
            return True
        return False

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
                f"  nursery.start_soon({async_fn.__name__}, ...)  # correct!"
            ) from None

        # Give good error for: nursery.start_soon(future)
        if _return_value_looks_like_wrong_library(async_fn):
            raise TypeError(
                "Trio was expecting an async function, but instead it got "
                f"{async_fn!r} – are you trying to use a library written for "
                "asyncio/twisted/tornado or similar? That won't work "
                "without some sort of compatibility shim."
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
                "That won't work without some sort of compatibility shim."
            )

        if inspect.isasyncgen(coro):
            raise TypeError(
                "start_soon expected an async function but got an async "
                f"generator {coro!r}"
            )

        # Give good error for: nursery.start_soon(some_sync_fn)
        raise TypeError(
            "Trio expected an async function, but {!r} appears to be "
            "synchronous".format(getattr(async_fn, "__qualname__", async_fn))
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


def async_wraps(
    cls: type[object],
    wrapped_cls: type[object],
    attr_name: str,
) -> Callable[[CallT], CallT]:
    """Similar to wraps, but for async wrappers of non-async functions."""

    def decorator(func: CallT) -> CallT:
        func.__name__ = attr_name
        func.__qualname__ = ".".join((cls.__qualname__, attr_name))

        func.__doc__ = f"Like :meth:`~{wrapped_cls.__module__}.{wrapped_cls.__qualname__}.{attr_name}`, but async."

        return func

    return decorator


def fixup_module_metadata(
    module_name: str, namespace: collections.abc.Mapping[str, object]
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


# We need ParamSpec to type this "properly", but that requires a runtime typing_extensions import
# to use as a class base. This is only used at runtime and isn't correct for type checkers anyway,
# so don't bother.
class generic_function(Generic[RetT]):
    """Decorator that makes a function indexable, to communicate
    non-inferrable generic type parameters to a static type checker.

    If you write::

        @generic_function
        def open_memory_channel(max_buffer_size: int) -> Tuple[
            SendChannel[T], ReceiveChannel[T]
        ]: ...

    it is valid at runtime to say ``open_memory_channel[bytes](5)``.
    This behaves identically to ``open_memory_channel(5)`` at runtime,
    and currently won't type-check without a mypy plugin or clever stubs,
    but at least it becomes possible to write those.
    """

    def __init__(self, fn: Callable[..., RetT]) -> None:
        update_wrapper(self, fn)
        self._fn = fn

    def __call__(self, *args: Any, **kwargs: Any) -> RetT:
        return self._fn(*args, **kwargs)

    def __getitem__(self, subscript: object) -> Self:
        return self


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
            f"{cls.__module__}.{cls.__qualname__} has no public constructor"
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
    Fn = TypeVar("Fn", bound=Callable[..., object])

    def wraps(
        wrapped: Callable[..., object],
        assigned: Sequence[str] = ...,
        updated: Sequence[str] = ...,
    ) -> Callable[[Fn], Fn]: ...

else:
    from functools import wraps  # noqa: F401  # this is re-exported
