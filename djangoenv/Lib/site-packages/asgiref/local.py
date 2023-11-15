import random
import string
import sys
import threading
import weakref


class Local:
    """
    A drop-in replacement for threading.locals that also works with asyncio
    Tasks (via the current_task asyncio method), and passes locals through
    sync_to_async and async_to_sync.

    Specifically:
     - Locals work per-coroutine on any thread not spawned using asgiref
     - Locals work per-thread on any thread not spawned using asgiref
     - Locals are shared with the parent coroutine when using sync_to_async
     - Locals are shared with the parent thread when using async_to_sync
       (and if that thread was launched using sync_to_async, with its parent
       coroutine as well, with this working for indefinite levels of nesting)

    Set thread_critical to True to not allow locals to pass from an async Task
    to a thread it spawns. This is needed for code that truly needs
    thread-safety, as opposed to things used for helpful context (e.g. sqlite
    does not like being called from a different thread to the one it is from).
    Thread-critical code will still be differentiated per-Task within a thread
    as it is expected it does not like concurrent access.

    This doesn't use contextvars as it needs to support 3.6. Once it can support
    3.7 only, we can then reimplement the storage more nicely.
    """

    def __init__(self, thread_critical: bool = False) -> None:
        self._thread_critical = thread_critical
        self._thread_lock = threading.RLock()
        self._context_refs: "weakref.WeakSet[object]" = weakref.WeakSet()
        # Random suffixes stop accidental reuse between different Locals,
        # though we try to force deletion as well.
        self._attr_name = "_asgiref_local_impl_{}_{}".format(
            id(self),
            "".join(random.choice(string.ascii_letters) for i in range(8)),
        )

    def _get_context_id(self):
        """
        Get the ID we should use for looking up variables
        """
        # Prevent a circular reference
        from .sync import AsyncToSync, SyncToAsync

        # First, pull the current task if we can
        context_id = SyncToAsync.get_current_task()
        context_is_async = True
        # OK, let's try for a thread ID
        if context_id is None:
            context_id = threading.current_thread()
            context_is_async = False
        # If we're thread-critical, we stop here, as we can't share contexts.
        if self._thread_critical:
            return context_id
        # Now, take those and see if we can resolve them through the launch maps
        for i in range(sys.getrecursionlimit()):
            try:
                if context_is_async:
                    # Tasks have a source thread in AsyncToSync
                    context_id = AsyncToSync.launch_map[context_id]
                    context_is_async = False
                else:
                    # Threads have a source task in SyncToAsync
                    context_id = SyncToAsync.launch_map[context_id]
                    context_is_async = True
            except KeyError:
                break
        else:
            # Catch infinite loops (they happen if you are screwing around
            # with AsyncToSync implementations)
            raise RuntimeError("Infinite launch_map loops")
        return context_id

    def _get_storage(self):
        context_obj = self._get_context_id()
        if not hasattr(context_obj, self._attr_name):
            setattr(context_obj, self._attr_name, {})
            self._context_refs.add(context_obj)
        return getattr(context_obj, self._attr_name)

    def __del__(self):
        try:
            for context_obj in self._context_refs:
                try:
                    delattr(context_obj, self._attr_name)
                except AttributeError:
                    pass
        except TypeError:
            # WeakSet.__iter__ can crash when interpreter is shutting down due
            # to _IterationGuard being None.
            pass

    def __getattr__(self, key):
        with self._thread_lock:
            storage = self._get_storage()
            if key in storage:
                return storage[key]
            else:
                raise AttributeError(f"{self!r} object has no attribute {key!r}")

    def __setattr__(self, key, value):
        if key in ("_context_refs", "_thread_critical", "_thread_lock", "_attr_name"):
            return super().__setattr__(key, value)
        with self._thread_lock:
            storage = self._get_storage()
            storage[key] = value

    def __delattr__(self, key):
        with self._thread_lock:
            storage = self._get_storage()
            if key in storage:
                del storage[key]
            else:
                raise AttributeError(f"{self!r} object has no attribute {key!r}")
