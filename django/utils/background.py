import asyncio
import concurrent.futures
import functools
import multiprocessing
import traceback

from django.conf import settings

try:
    import contextvars  # Python 3.7+ only.
except ImportError:  # pragma: no cover
    contextvars = None  # type: ignore




async def run_in_threadpool(func, *args, **kwargs):
    loop = asyncio.get_event_loop()

    if contextvars is not None:  # pragma: no cover
        # Ensure we run in the same context
        child = functools.partial(func, *args, **kwargs)
        context = contextvars.copy_context()
        func = context.run
        args = (child,)
    elif kwargs:  # pragma: no cover
        # loop.run_in_executor doesn't accept 'kwargs', so bind them in here
        func = functools.partial(func, **kwargs)

    return await loop.run_in_executor(None, func, *args)


class BackgroundTask:
    def __init__(self, n=None):
        """Initialise :class:`~concurrent.futures.ThreadPoolExecutor`
        :param n: int number of workers for :class:`~concurrent.futures.ThreadPoolExecutor`
        """
        if n is None:
            n = multiprocessing.cpu_count()

        self.n = n
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=n)
        self.results = []

    def run(self, f, *args, **kwargs):
        self.pool._max_workers = self.n
        self.pool._adjust_thread_count()

        f = self.pool.submit(f, *args, **kwargs)
        self.results.append(f)
        return f

    def task(self, f):
        def on_future_done(fs):
            try:
                fs.result()
            except:
                traceback.print_exc()

        def do_task(*args, **kwargs):
            result = self.run(f, *args, **kwargs)
            result.add_done_callback(on_future_done)
            return result

        return do_task

    async def __call__(self, func, *args, **kwargs) -> None:
        if asyncio.iscoroutinefunction(func):
            return await asyncio.ensure_future(func(*args, **kwargs))

        return await run_in_threadpool(func, *args, **kwargs)


task = BackgroundTask(n=settings.BACKGROUND_TASK_POOL_SIZE)
