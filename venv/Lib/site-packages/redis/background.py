import asyncio
import threading
from typing import Any, Callable, Coroutine


class BackgroundScheduler:
    """
    Schedules background tasks execution either in separate thread or in the running event loop.
    """

    def __init__(self):
        self._next_timer = None
        self._event_loops = []
        self._lock = threading.Lock()
        self._stopped = False

    def __del__(self):
        self.stop()

    def stop(self):
        """
        Stop all scheduled tasks and clean up resources.
        """
        with self._lock:
            if self._stopped:
                return
            self._stopped = True

            if self._next_timer:
                self._next_timer.cancel()
                self._next_timer = None

            # Stop all event loops
            for loop in self._event_loops:
                if loop.is_running():
                    loop.call_soon_threadsafe(loop.stop)

            self._event_loops.clear()

    def run_once(self, delay: float, callback: Callable, *args):
        """
        Runs callable task once after certain delay in seconds.
        """
        with self._lock:
            if self._stopped:
                return

        # Run loop in a separate thread to unblock main thread.
        loop = asyncio.new_event_loop()

        with self._lock:
            self._event_loops.append(loop)

        thread = threading.Thread(
            target=_start_event_loop_in_thread,
            args=(loop, self._call_later, delay, callback, *args),
            daemon=True,
        )
        thread.start()

    def run_recurring(self, interval: float, callback: Callable, *args):
        """
        Runs recurring callable task with given interval in seconds.
        """
        with self._lock:
            if self._stopped:
                return

        # Run loop in a separate thread to unblock main thread.
        loop = asyncio.new_event_loop()

        with self._lock:
            self._event_loops.append(loop)

        thread = threading.Thread(
            target=_start_event_loop_in_thread,
            args=(loop, self._call_later_recurring, interval, callback, *args),
            daemon=True,
        )
        thread.start()

    async def run_recurring_async(
        self, interval: float, coro: Callable[..., Coroutine[Any, Any, Any]], *args
    ):
        """
        Runs recurring coroutine with given interval in seconds in the current event loop.
        To be used only from an async context. No additional threads are created.
        """
        with self._lock:
            if self._stopped:
                return

        loop = asyncio.get_running_loop()
        wrapped = _async_to_sync_wrapper(loop, coro, *args)

        def tick():
            with self._lock:
                if self._stopped:
                    return
            # Schedule the coroutine
            wrapped()
            # Schedule next tick
            self._next_timer = loop.call_later(interval, tick)

        # Schedule first tick
        self._next_timer = loop.call_later(interval, tick)

    def _call_later(
        self, loop: asyncio.AbstractEventLoop, delay: float, callback: Callable, *args
    ):
        with self._lock:
            if self._stopped:
                return
        self._next_timer = loop.call_later(delay, callback, *args)

    def _call_later_recurring(
        self,
        loop: asyncio.AbstractEventLoop,
        interval: float,
        callback: Callable,
        *args,
    ):
        with self._lock:
            if self._stopped:
                return
        self._call_later(
            loop, interval, self._execute_recurring, loop, interval, callback, *args
        )

    def _execute_recurring(
        self,
        loop: asyncio.AbstractEventLoop,
        interval: float,
        callback: Callable,
        *args,
    ):
        """
        Executes recurring callable task with given interval in seconds.
        """
        with self._lock:
            if self._stopped:
                return

        try:
            callback(*args)
        except Exception:
            # Silently ignore exceptions during shutdown
            pass

        with self._lock:
            if self._stopped:
                return

        self._call_later(
            loop, interval, self._execute_recurring, loop, interval, callback, *args
        )


def _start_event_loop_in_thread(
    event_loop: asyncio.AbstractEventLoop, call_soon_cb: Callable, *args
):
    """
    Starts event loop in a thread and schedule callback as soon as event loop is ready.
    Used to be able to schedule tasks using loop.call_later.

    :param event_loop:
    :return:
    """
    asyncio.set_event_loop(event_loop)
    event_loop.call_soon(call_soon_cb, event_loop, *args)
    try:
        event_loop.run_forever()
    finally:
        try:
            # Clean up pending tasks
            pending = asyncio.all_tasks(event_loop)
            for task in pending:
                task.cancel()
            # Run loop once more to process cancellations
            event_loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        except Exception:
            pass
        finally:
            event_loop.close()


def _async_to_sync_wrapper(loop, coro_func, *args, **kwargs):
    """
    Wraps an asynchronous function so it can be used with loop.call_later.

    :param loop: The event loop in which the coroutine will be executed.
    :param coro_func: The coroutine function to wrap.
    :param args: Positional arguments to pass to the coroutine function.
    :param kwargs: Keyword arguments to pass to the coroutine function.
    :return: A regular function suitable for loop.call_later.
    """

    def wrapped():
        # Schedule the coroutine in the event loop
        asyncio.ensure_future(coro_func(*args, **kwargs), loop=loop)

    return wrapped
