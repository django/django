import asyncio
from collections import OrderedDict
from functools import _CacheInfo, _make_key, partial, wraps

__all__ = ("alru_cache",)


def unpartial(fn):
    while hasattr(fn, "func"):
        fn = fn.func

    return fn


def _done_callback(fut, task):
    if task.cancelled():
        fut.cancel()
        return

    exc = task.exception()
    if exc is not None:
        fut.set_exception(exc)
        return

    fut.set_result(task.result())


def _cache_invalidate(wrapped, typed, *args, **kwargs):
    key = _make_key(args, kwargs, typed)

    exists = key in wrapped._cache

    if exists:
        wrapped._cache.pop(key)

    return exists


def _cache_clear(wrapped):
    wrapped.hits = wrapped.misses = 0
    wrapped._cache = OrderedDict()
    wrapped.tasks = set()


def _open(wrapped):
    if not wrapped.closed:
        raise RuntimeError("alru_cache is not closed")

    was_closed = (
        wrapped.hits == wrapped.misses == len(wrapped.tasks) == len(wrapped._cache) == 0
    )

    if not was_closed:
        raise RuntimeError("alru_cache was not closed correctly")

    wrapped.closed = False


def _close(wrapped, *, cancel=False, return_exceptions=True):
    if wrapped.closed:
        raise RuntimeError("alru_cache is closed")

    wrapped.closed = True

    if cancel:
        for task in wrapped.tasks:
            if not task.done():  # not sure is it possible
                task.cancel()

    return _wait_closed(wrapped, return_exceptions=return_exceptions)


async def _wait_closed(wrapped, *, return_exceptions):
    wait_closed = asyncio.gather(*wrapped.tasks, return_exceptions=return_exceptions)

    wait_closed.add_done_callback(partial(_close_waited, wrapped))

    ret = await wait_closed

    # hack to get _close_waited callback to be executed
    await asyncio.sleep(0)

    return ret


def _close_waited(wrapped, _):
    wrapped.cache_clear()


def _cache_info(wrapped, maxsize):
    return _CacheInfo(
        wrapped.hits,
        wrapped.misses,
        maxsize,
        len(wrapped._cache),
    )


def __cache_touch(wrapped, key):
    try:
        wrapped._cache.move_to_end(key)
    except KeyError:  # not sure is it possible
        pass


def _cache_hit(wrapped, key):
    wrapped.hits += 1
    __cache_touch(wrapped, key)


def _cache_miss(wrapped, key):
    wrapped.misses += 1
    __cache_touch(wrapped, key)


def alru_cache(
    fn=None,
    maxsize=128,
    typed=False,
    *,
    cache_exceptions=True,
):
    """From https://github.com/aio-libs/async-lru"""

    def wrapper(fn):
        _origin = unpartial(fn)

        if not asyncio.iscoroutinefunction(_origin):
            raise RuntimeError("Coroutine function is required, got {}".format(fn))

        # functools.partialmethod support
        if hasattr(fn, "_make_unbound_method"):
            fn = fn._make_unbound_method()

        @wraps(fn)
        async def wrapped(*fn_args, **fn_kwargs):
            if wrapped.closed:
                raise RuntimeError("alru_cache is closed for {}".format(wrapped))

            loop = asyncio.get_event_loop()

            key = _make_key(fn_args, fn_kwargs, typed)

            fut = wrapped._cache.get(key)

            if fut is not None:
                if not fut.done():
                    _cache_hit(wrapped, key)
                    return await asyncio.shield(fut)

                exc = fut._exception

                if exc is None or cache_exceptions:
                    _cache_hit(wrapped, key)
                    return fut.result()

                # exception here and cache_exceptions == False
                wrapped._cache.pop(key)

            fut = loop.create_future()
            task = loop.create_task(fn(*fn_args, **fn_kwargs))
            task.add_done_callback(partial(_done_callback, fut))

            wrapped.tasks.add(task)
            task.add_done_callback(wrapped.tasks.remove)

            wrapped._cache[key] = fut

            if maxsize is not None and len(wrapped._cache) > maxsize:
                wrapped._cache.popitem(last=False)

            _cache_miss(wrapped, key)
            return await asyncio.shield(fut)

        _cache_clear(wrapped)
        wrapped._origin = _origin
        wrapped.closed = False
        wrapped.cache_info = partial(_cache_info, wrapped, maxsize)
        wrapped.cache_clear = partial(_cache_clear, wrapped)
        wrapped.invalidate = partial(_cache_invalidate, wrapped, typed)
        wrapped.close = partial(_close, wrapped)
        wrapped.open = partial(_open, wrapped)

        return wrapped

    if fn is None:
        return wrapper

    if callable(fn) or hasattr(fn, "_make_unbound_method"):
        return wrapper(fn)

    raise NotImplementedError("{} decorating is not supported".format(fn))
