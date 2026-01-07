import sys
import threading
from collections import deque
from concurrent.futures import Executor, Future
from typing import Any, Callable, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

_T = TypeVar("_T")
_P = ParamSpec("_P")
_R = TypeVar("_R")


class _WorkItem:
    """
    Represents an item needing to be run in the executor.
    Copied from ThreadPoolExecutor (but it's private, so we're not going to rely on importing it)
    """

    def __init__(
        self,
        future: "Future[_R]",
        fn: Callable[_P, _R],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        __traceback_hide__ = True  # noqa: F841
        if not self.future.set_running_or_notify_cancel():
            return
        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException as exc:
            self.future.set_exception(exc)
            # Break a reference cycle with the exception 'exc'
            self = None  # type: ignore[assignment]
        else:
            self.future.set_result(result)


class CurrentThreadExecutor(Executor):
    """
    An Executor that actually runs code in the thread it is instantiated in.
    Passed to other threads running async code, so they can run sync code in
    the thread they came from.
    """

    def __init__(self, old_executor: "CurrentThreadExecutor | None") -> None:
        self._work_thread = threading.current_thread()
        self._work_ready = threading.Condition(threading.Lock())
        self._work_items = deque[_WorkItem]()  # synchronized by _work_ready
        self._broken = False  # synchronized by _work_ready
        self._old_executor = old_executor

    def run_until_future(self, future: "Future[Any]") -> None:
        """
        Runs the code in the work queue until a result is available from the future.
        Should be run from the thread the executor is initialised in.
        """
        # Check we're in the right thread
        if threading.current_thread() != self._work_thread:
            raise RuntimeError(
                "You cannot run CurrentThreadExecutor from a different thread"
            )

        def done(future: "Future[Any]") -> None:
            with self._work_ready:
                self._broken = True
                self._work_ready.notify()

        future.add_done_callback(done)
        # Keep getting and running work items until the future we're waiting for
        # is done and the queue is empty.
        while True:
            with self._work_ready:
                while not self._work_items and not self._broken:
                    self._work_ready.wait()
                if not self._work_items:
                    break
                # Get a work item and run it
                work_item = self._work_items.popleft()
            work_item.run()
            del work_item

    def submit(
        self,
        fn: Callable[_P, _R],
        /,
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> "Future[_R]":
        # Check they're not submitting from the same thread
        if threading.current_thread() == self._work_thread:
            raise RuntimeError(
                "You cannot submit onto CurrentThreadExecutor from its own thread"
            )
        f: "Future[_R]" = Future()
        work_item = _WorkItem(f, fn, *args, **kwargs)

        # Walk up the CurrentThreadExecutor stack to find the closest one still
        # running
        executor = self
        while True:
            with executor._work_ready:
                if not executor._broken:
                    # Add to work queue
                    executor._work_items.append(work_item)
                    executor._work_ready.notify()
                    break
            if executor._old_executor is None:
                raise RuntimeError("CurrentThreadExecutor already quit or is broken")
            executor = executor._old_executor

        # Return the future
        return f
