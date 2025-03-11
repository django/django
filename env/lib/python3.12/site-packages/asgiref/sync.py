import asyncio
import asyncio.coroutines
import contextvars
import functools
import inspect
import os
import sys
import threading
import warnings
import weakref
from concurrent.futures import Future, ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)

from .current_thread_executor import CurrentThreadExecutor
from .local import Local

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    # This is not available to import at runtime
    from _typeshed import OptExcInfo

_F = TypeVar("_F", bound=Callable[..., Any])
_P = ParamSpec("_P")
_R = TypeVar("_R")


def _restore_context(context: contextvars.Context) -> None:
    # Check for changes in contextvars, and set them to the current
    # context for downstream consumers
    for cvar in context:
        cvalue = context.get(cvar)
        try:
            if cvar.get() != cvalue:
                cvar.set(cvalue)
        except LookupError:
            cvar.set(cvalue)


# Python 3.12 deprecates asyncio.iscoroutinefunction() as an alias for
# inspect.iscoroutinefunction(), whilst also removing the _is_coroutine marker.
# The latter is replaced with the inspect.markcoroutinefunction decorator.
# Until 3.12 is the minimum supported Python version, provide a shim.

if hasattr(inspect, "markcoroutinefunction"):
    iscoroutinefunction = inspect.iscoroutinefunction
    markcoroutinefunction: Callable[[_F], _F] = inspect.markcoroutinefunction
else:
    iscoroutinefunction = asyncio.iscoroutinefunction  # type: ignore[assignment]

    def markcoroutinefunction(func: _F) -> _F:
        func._is_coroutine = asyncio.coroutines._is_coroutine  # type: ignore
        return func


class ThreadSensitiveContext:
    """Async context manager to manage context for thread sensitive mode

    This context manager controls which thread pool executor is used when in
    thread sensitive mode. By default, a single thread pool executor is shared
    within a process.

    The ThreadSensitiveContext() context manager may be used to specify a
    thread pool per context.

    This context manager is re-entrant, so only the outer-most call to
    ThreadSensitiveContext will set the context.

    Usage:

    >>> import time
    >>> async with ThreadSensitiveContext():
    ...     await sync_to_async(time.sleep, 1)()
    """

    def __init__(self):
        self.token = None

    async def __aenter__(self):
        try:
            SyncToAsync.thread_sensitive_context.get()
        except LookupError:
            self.token = SyncToAsync.thread_sensitive_context.set(self)

        return self

    async def __aexit__(self, exc, value, tb):
        if not self.token:
            return

        executor = SyncToAsync.context_to_thread_executor.pop(self, None)
        if executor:
            executor.shutdown()
        SyncToAsync.thread_sensitive_context.reset(self.token)


class AsyncToSync(Generic[_P, _R]):
    """
    Utility class which turns an awaitable that only works on the thread with
    the event loop into a synchronous callable that works in a subthread.

    If the call stack contains an async loop, the code runs there.
    Otherwise, the code runs in a new loop in a new thread.

    Either way, this thread then pauses and waits to run any thread_sensitive
    code called from further down the call stack using SyncToAsync, before
    finally exiting once the async task returns.
    """

    # Keeps a reference to the CurrentThreadExecutor in local context, so that
    # any sync_to_async inside the wrapped code can find it.
    executors: "Local" = Local()

    # When we can't find a CurrentThreadExecutor from the context, such as
    # inside create_task, we'll look it up here from the running event loop.
    loop_thread_executors: "Dict[asyncio.AbstractEventLoop, CurrentThreadExecutor]" = {}

    def __init__(
        self,
        awaitable: Union[
            Callable[_P, Coroutine[Any, Any, _R]],
            Callable[_P, Awaitable[_R]],
        ],
        force_new_loop: bool = False,
    ):
        if not callable(awaitable) or (
            not iscoroutinefunction(awaitable)
            and not iscoroutinefunction(getattr(awaitable, "__call__", awaitable))
        ):
            # Python does not have very reliable detection of async functions
            # (lots of false negatives) so this is just a warning.
            warnings.warn(
                "async_to_sync was passed a non-async-marked callable", stacklevel=2
            )
        self.awaitable = awaitable
        try:
            self.__self__ = self.awaitable.__self__  # type: ignore[union-attr]
        except AttributeError:
            pass
        self.force_new_loop = force_new_loop
        self.main_event_loop = None
        try:
            self.main_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # There's no event loop in this thread.
            pass

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        __traceback_hide__ = True  # noqa: F841

        if not self.force_new_loop and not self.main_event_loop:
            # There's no event loop in this thread. Look for the threadlocal if
            # we're inside SyncToAsync
            main_event_loop_pid = getattr(
                SyncToAsync.threadlocal, "main_event_loop_pid", None
            )
            # We make sure the parent loop is from the same process - if
            # they've forked, this is not going to be valid any more (#194)
            if main_event_loop_pid and main_event_loop_pid == os.getpid():
                self.main_event_loop = getattr(
                    SyncToAsync.threadlocal, "main_event_loop", None
                )

        # You can't call AsyncToSync from a thread with a running event loop
        try:
            event_loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            if event_loop.is_running():
                raise RuntimeError(
                    "You cannot use AsyncToSync in the same thread as an async event loop - "
                    "just await the async function directly."
                )

        # Make a future for the return information
        call_result: "Future[_R]" = Future()

        # Make a CurrentThreadExecutor we'll use to idle in this thread - we
        # need one for every sync frame, even if there's one above us in the
        # same thread.
        old_executor = getattr(self.executors, "current", None)
        current_executor = CurrentThreadExecutor()
        self.executors.current = current_executor

        # Wrapping context in list so it can be reassigned from within
        # `main_wrap`.
        context = [contextvars.copy_context()]

        # Get task context so that parent task knows which task to propagate
        # an asyncio.CancelledError to.
        task_context = getattr(SyncToAsync.threadlocal, "task_context", None)

        loop = None
        # Use call_soon_threadsafe to schedule a synchronous callback on the
        # main event loop's thread if it's there, otherwise make a new loop
        # in this thread.
        try:
            awaitable = self.main_wrap(
                call_result,
                sys.exc_info(),
                task_context,
                context,
                *args,
                **kwargs,
            )

            if not (self.main_event_loop and self.main_event_loop.is_running()):
                # Make our own event loop - in a new thread - and run inside that.
                loop = asyncio.new_event_loop()
                self.loop_thread_executors[loop] = current_executor
                loop_executor = ThreadPoolExecutor(max_workers=1)
                loop_future = loop_executor.submit(
                    self._run_event_loop, loop, awaitable
                )
                if current_executor:
                    # Run the CurrentThreadExecutor until the future is done
                    current_executor.run_until_future(loop_future)
                # Wait for future and/or allow for exception propagation
                loop_future.result()
            else:
                # Call it inside the existing loop
                self.main_event_loop.call_soon_threadsafe(
                    self.main_event_loop.create_task, awaitable
                )
                if current_executor:
                    # Run the CurrentThreadExecutor until the future is done
                    current_executor.run_until_future(call_result)
        finally:
            # Clean up any executor we were running
            if loop is not None:
                del self.loop_thread_executors[loop]
            _restore_context(context[0])
            # Restore old current thread executor state
            self.executors.current = old_executor

        # Wait for results from the future.
        return call_result.result()

    def _run_event_loop(self, loop, coro):
        """
        Runs the given event loop (designed to be called in a thread).
        """
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            try:
                # mimic asyncio.run() behavior
                # cancel unexhausted async generators
                tasks = asyncio.all_tasks(loop)
                for task in tasks:
                    task.cancel()

                async def gather():
                    await asyncio.gather(*tasks, return_exceptions=True)

                loop.run_until_complete(gather())
                for task in tasks:
                    if task.cancelled():
                        continue
                    if task.exception() is not None:
                        loop.call_exception_handler(
                            {
                                "message": "unhandled exception during loop shutdown",
                                "exception": task.exception(),
                                "task": task,
                            }
                        )
                if hasattr(loop, "shutdown_asyncgens"):
                    loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()
                asyncio.set_event_loop(self.main_event_loop)

    def __get__(self, parent: Any, objtype: Any) -> Callable[_P, _R]:
        """
        Include self for methods
        """
        func = functools.partial(self.__call__, parent)
        return functools.update_wrapper(func, self.awaitable)

    async def main_wrap(
        self,
        call_result: "Future[_R]",
        exc_info: "OptExcInfo",
        task_context: "Optional[List[asyncio.Task[Any]]]",
        context: List[contextvars.Context],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None:
        """
        Wraps the awaitable with something that puts the result into the
        result/exception future.
        """

        __traceback_hide__ = True  # noqa: F841

        if context is not None:
            _restore_context(context[0])

        current_task = asyncio.current_task()
        if current_task is not None and task_context is not None:
            task_context.append(current_task)

        try:
            # If we have an exception, run the function inside the except block
            # after raising it so exc_info is correctly populated.
            if exc_info[1]:
                try:
                    raise exc_info[1]
                except BaseException:
                    result = await self.awaitable(*args, **kwargs)
            else:
                result = await self.awaitable(*args, **kwargs)
        except BaseException as e:
            call_result.set_exception(e)
        else:
            call_result.set_result(result)
        finally:
            if current_task is not None and task_context is not None:
                task_context.remove(current_task)
            context[0] = contextvars.copy_context()


class SyncToAsync(Generic[_P, _R]):
    """
    Utility class which turns a synchronous callable into an awaitable that
    runs in a threadpool. It also sets a threadlocal inside the thread so
    calls to AsyncToSync can escape it.

    If thread_sensitive is passed, the code will run in the same thread as any
    outer code. This is needed for underlying Python code that is not
    threadsafe (for example, code which handles SQLite database connections).

    If the outermost program is async (i.e. SyncToAsync is outermost), then
    this will be a dedicated single sub-thread that all sync code runs in,
    one after the other. If the outermost program is sync (i.e. AsyncToSync is
    outermost), this will just be the main thread. This is achieved by idling
    with a CurrentThreadExecutor while AsyncToSync is blocking its sync parent,
    rather than just blocking.

    If executor is passed in, that will be used instead of the loop's default executor.
    In order to pass in an executor, thread_sensitive must be set to False, otherwise
    a TypeError will be raised.
    """

    # Storage for main event loop references
    threadlocal = threading.local()

    # Single-thread executor for thread-sensitive code
    single_thread_executor = ThreadPoolExecutor(max_workers=1)

    # Maintain a contextvar for the current execution context. Optionally used
    # for thread sensitive mode.
    thread_sensitive_context: "contextvars.ContextVar[ThreadSensitiveContext]" = (
        contextvars.ContextVar("thread_sensitive_context")
    )

    # Contextvar that is used to detect if the single thread executor
    # would be awaited on while already being used in the same context
    deadlock_context: "contextvars.ContextVar[bool]" = contextvars.ContextVar(
        "deadlock_context"
    )

    # Maintaining a weak reference to the context ensures that thread pools are
    # erased once the context goes out of scope. This terminates the thread pool.
    context_to_thread_executor: "weakref.WeakKeyDictionary[ThreadSensitiveContext, ThreadPoolExecutor]" = (
        weakref.WeakKeyDictionary()
    )

    def __init__(
        self,
        func: Callable[_P, _R],
        thread_sensitive: bool = True,
        executor: Optional["ThreadPoolExecutor"] = None,
    ) -> None:
        if (
            not callable(func)
            or iscoroutinefunction(func)
            or iscoroutinefunction(getattr(func, "__call__", func))
        ):
            raise TypeError("sync_to_async can only be applied to sync functions.")
        self.func = func
        functools.update_wrapper(self, func)
        self._thread_sensitive = thread_sensitive
        markcoroutinefunction(self)
        if thread_sensitive and executor is not None:
            raise TypeError("executor must not be set when thread_sensitive is True")
        self._executor = executor
        try:
            self.__self__ = func.__self__  # type: ignore
        except AttributeError:
            pass

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        __traceback_hide__ = True  # noqa: F841
        loop = asyncio.get_running_loop()

        # Work out what thread to run the code in
        if self._thread_sensitive:
            current_thread_executor = getattr(AsyncToSync.executors, "current", None)
            if current_thread_executor:
                # If we have a parent sync thread above somewhere, use that
                executor = current_thread_executor
            elif self.thread_sensitive_context.get(None):
                # If we have a way of retrieving the current context, attempt
                # to use a per-context thread pool executor
                thread_sensitive_context = self.thread_sensitive_context.get()

                if thread_sensitive_context in self.context_to_thread_executor:
                    # Re-use thread executor in current context
                    executor = self.context_to_thread_executor[thread_sensitive_context]
                else:
                    # Create new thread executor in current context
                    executor = ThreadPoolExecutor(max_workers=1)
                    self.context_to_thread_executor[thread_sensitive_context] = executor
            elif loop in AsyncToSync.loop_thread_executors:
                # Re-use thread executor for running loop
                executor = AsyncToSync.loop_thread_executors[loop]
            elif self.deadlock_context.get(False):
                raise RuntimeError(
                    "Single thread executor already being used, would deadlock"
                )
            else:
                # Otherwise, we run it in a fixed single thread
                executor = self.single_thread_executor
                self.deadlock_context.set(True)
        else:
            # Use the passed in executor, or the loop's default if it is None
            executor = self._executor

        context = contextvars.copy_context()
        child = functools.partial(self.func, *args, **kwargs)
        func = context.run
        task_context: List[asyncio.Task[Any]] = []

        # Run the code in the right thread
        exec_coro = loop.run_in_executor(
            executor,
            functools.partial(
                self.thread_handler,
                loop,
                sys.exc_info(),
                task_context,
                func,
                child,
            ),
        )
        ret: _R
        try:
            ret = await asyncio.shield(exec_coro)
        except asyncio.CancelledError:
            cancel_parent = True
            try:
                task = task_context[0]
                task.cancel()
                try:
                    await task
                    cancel_parent = False
                except asyncio.CancelledError:
                    pass
            except IndexError:
                pass
            if exec_coro.done():
                raise
            if cancel_parent:
                exec_coro.cancel()
            ret = await exec_coro
        finally:
            _restore_context(context)
            self.deadlock_context.set(False)

        return ret

    def __get__(
        self, parent: Any, objtype: Any
    ) -> Callable[_P, Coroutine[Any, Any, _R]]:
        """
        Include self for methods
        """
        func = functools.partial(self.__call__, parent)
        return functools.update_wrapper(func, self.func)

    def thread_handler(self, loop, exc_info, task_context, func, *args, **kwargs):
        """
        Wraps the sync application with exception handling.
        """

        __traceback_hide__ = True  # noqa: F841

        # Set the threadlocal for AsyncToSync
        self.threadlocal.main_event_loop = loop
        self.threadlocal.main_event_loop_pid = os.getpid()
        self.threadlocal.task_context = task_context

        # Run the function
        # If we have an exception, run the function inside the except block
        # after raising it so exc_info is correctly populated.
        if exc_info[1]:
            try:
                raise exc_info[1]
            except BaseException:
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)


@overload
def async_to_sync(
    *,
    force_new_loop: bool = False,
) -> Callable[
    [Union[Callable[_P, Coroutine[Any, Any, _R]], Callable[_P, Awaitable[_R]]]],
    Callable[_P, _R],
]:
    ...


@overload
def async_to_sync(
    awaitable: Union[
        Callable[_P, Coroutine[Any, Any, _R]],
        Callable[_P, Awaitable[_R]],
    ],
    *,
    force_new_loop: bool = False,
) -> Callable[_P, _R]:
    ...


def async_to_sync(
    awaitable: Optional[
        Union[
            Callable[_P, Coroutine[Any, Any, _R]],
            Callable[_P, Awaitable[_R]],
        ]
    ] = None,
    *,
    force_new_loop: bool = False,
) -> Union[
    Callable[
        [Union[Callable[_P, Coroutine[Any, Any, _R]], Callable[_P, Awaitable[_R]]]],
        Callable[_P, _R],
    ],
    Callable[_P, _R],
]:
    if awaitable is None:
        return lambda f: AsyncToSync(
            f,
            force_new_loop=force_new_loop,
        )
    return AsyncToSync(
        awaitable,
        force_new_loop=force_new_loop,
    )


@overload
def sync_to_async(
    *,
    thread_sensitive: bool = True,
    executor: Optional["ThreadPoolExecutor"] = None,
) -> Callable[[Callable[_P, _R]], Callable[_P, Coroutine[Any, Any, _R]]]:
    ...


@overload
def sync_to_async(
    func: Callable[_P, _R],
    *,
    thread_sensitive: bool = True,
    executor: Optional["ThreadPoolExecutor"] = None,
) -> Callable[_P, Coroutine[Any, Any, _R]]:
    ...


def sync_to_async(
    func: Optional[Callable[_P, _R]] = None,
    *,
    thread_sensitive: bool = True,
    executor: Optional["ThreadPoolExecutor"] = None,
) -> Union[
    Callable[[Callable[_P, _R]], Callable[_P, Coroutine[Any, Any, _R]]],
    Callable[_P, Coroutine[Any, Any, _R]],
]:
    if func is None:
        return lambda f: SyncToAsync(
            f,
            thread_sensitive=thread_sensitive,
            executor=executor,
        )
    return SyncToAsync(
        func,
        thread_sensitive=thread_sensitive,
        executor=executor,
    )
