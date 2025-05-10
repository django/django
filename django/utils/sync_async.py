import functools
import inspect


async def run_async_generator(gen):
    """
    Run a generator-based coroutine that yields awaitables.
    """
    res = None

    try:
        while True:
            try:
                res = gen.send(res)
                if inspect.isawaitable(res):
                    res = await res
            except Exception as e:
                res = gen.throw(e)
    except StopIteration:
        pass

    return res


def run_sync_generator(gen):
    """
    Run a generator-based coroutine in a synchronous context.
    """
    res = None

    try:
        while True:
            try:
                res = gen.send(res)
            except Exception as e:
                res = gen.throw(e)
    except StopIteration:
        pass

    return res


def sync_async_method_adapter(fn):
    """
    A decorator for methods that return a generator-based coroutine
    (sync or async). It uses the class's `sync_async_adapter`
    method to execute the coroutine depending on the context
    (e.g., run_async_generator or run_sync_generator).

    Example:

        class Base:
            @sync_async_method_adapter
            def my_method(self):
                yield self.client().get()

        class Async(Base):
            sync_async_adapter = run_async_generator
            client = AsyncClient

        class Sync(Base):
            sync_async_adapter = run_sync_generator
            client = SyncClient
    """
    @functools.wraps(fn)
    def inner(self, *args, **kwargs):
        adapter = getattr(self.__class__, 'sync_async_adapter', None)

        if not callable(adapter):
            raise TypeError(
                f"{self.__class__.__name__} must "
                "define a 'sync_async_adapter' method"
            )
        return adapter(fn(self, *args, **kwargs))

    return inner
