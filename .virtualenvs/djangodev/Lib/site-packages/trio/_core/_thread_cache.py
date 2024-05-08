from __future__ import annotations

import ctypes
import ctypes.util
import sys
import traceback
from functools import partial
from itertools import count
from threading import Lock, Thread
from typing import Any, Callable, Generic, TypeVar

import outcome

RetT = TypeVar("RetT")


def _to_os_thread_name(name: str) -> bytes:
    # ctypes handles the trailing \00
    return name.encode("ascii", errors="replace")[:15]


# used to construct the method used to set os thread name, or None, depending on platform.
# called once on import
def get_os_thread_name_func() -> Callable[[int | None, str], None] | None:
    def namefunc(
        setname: Callable[[int, bytes], int], ident: int | None, name: str
    ) -> None:
        # Thread.ident is None "if it has not been started". Unclear if that can happen
        # with current usage.
        if ident is not None:  # pragma: no cover
            setname(ident, _to_os_thread_name(name))

    # namefunc on Mac also takes an ident, even if pthread_setname_np doesn't/can't use it
    # so the caller don't need to care about platform.
    def darwin_namefunc(
        setname: Callable[[bytes], int], ident: int | None, name: str
    ) -> None:
        # I don't know if Mac can rename threads that hasn't been started, but default
        # to no to be on the safe side.
        if ident is not None:  # pragma: no cover
            setname(_to_os_thread_name(name))

    # find the pthread library
    # this will fail on windows and musl
    libpthread_path = ctypes.util.find_library("pthread")
    if not libpthread_path:
        # musl includes pthread functions directly in libc.so
        # (but note that find_library("c") does not work on musl,
        #  see: https://github.com/python/cpython/issues/65821)
        # so try that library instead
        # if it doesn't exist, CDLL() will fail below
        libpthread_path = "libc.so"

    # Sometimes windows can find the path, but gives a permission error when
    # accessing it. Catching a wider exception in case of more esoteric errors.
    # https://github.com/python-trio/trio/issues/2688
    try:
        libpthread = ctypes.CDLL(libpthread_path)
    except Exception:  # pragma: no cover
        return None

    # get the setname method from it
    # afaik this should never fail
    pthread_setname_np = getattr(libpthread, "pthread_setname_np", None)
    if pthread_setname_np is None:  # pragma: no cover
        return None

    # specify function prototype
    pthread_setname_np.restype = ctypes.c_int

    # on mac OSX pthread_setname_np does not take a thread id,
    # it only lets threads name themselves, which is not a problem for us.
    # Just need to make sure to call it correctly
    if sys.platform == "darwin":
        pthread_setname_np.argtypes = [ctypes.c_char_p]
        return partial(darwin_namefunc, pthread_setname_np)

    # otherwise assume linux parameter conventions. Should also work on *BSD
    pthread_setname_np.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    return partial(namefunc, pthread_setname_np)


# construct os thread name method
set_os_thread_name = get_os_thread_name_func()

# The "thread cache" is a simple unbounded thread pool, i.e., it automatically
# spawns as many threads as needed to handle all the requests its given. Its
# only purpose is to cache worker threads so that they don't have to be
# started from scratch every time we want to delegate some work to a thread.
# It's expected that some higher-level code will track how many threads are in
# use to avoid overwhelming the system (e.g. the limiter= argument to
# trio.to_thread.run_sync).
#
# To maximize sharing, there's only one thread cache per process, even if you
# have multiple calls to trio.run.
#
# Guarantees:
#
# It's safe to call start_thread_soon simultaneously from
# multiple threads.
#
# Idle threads are chosen in LIFO order, i.e. we *don't* spread work evenly
# over all threads. Instead we try to let some threads do most of the work
# while others sit idle as much as possible. Compared to FIFO, this has better
# memory cache behavior, and it makes it easier to detect when we have too
# many threads, so idle ones can exit.
#
# This code assumes that 'dict' has the following properties:
#
# - __setitem__, __delitem__, and popitem are all thread-safe and atomic with
#   respect to each other. This is guaranteed by the GIL.
#
# - popitem returns the most-recently-added item (i.e., __setitem__ + popitem
#   give you a LIFO queue). This relies on dicts being insertion-ordered, like
#   they are in py36+.

# How long a thread will idle waiting for new work before gives up and exits.
# This value is pretty arbitrary; I don't think it matters too much.
IDLE_TIMEOUT = 10  # seconds

name_counter = count()


class WorkerThread(Generic[RetT]):
    def __init__(self, thread_cache: ThreadCache) -> None:
        self._job: (
            tuple[
                Callable[[], RetT],
                Callable[[outcome.Outcome[RetT]], object],
                str | None,
            ]
            | None
        ) = None
        self._thread_cache = thread_cache
        # This Lock is used in an unconventional way.
        #
        # "Unlocked" means we have a pending job that's been assigned to us;
        # "locked" means that we don't.
        #
        # Initially we have no job, so it starts out in locked state.
        self._worker_lock = Lock()
        self._worker_lock.acquire()
        self._default_name = f"Trio thread {next(name_counter)}"

        self._thread = Thread(target=self._work, name=self._default_name, daemon=True)

        if set_os_thread_name:
            set_os_thread_name(self._thread.ident, self._default_name)
        self._thread.start()

    def _handle_job(self) -> None:
        # Handle job in a separate method to ensure user-created
        # objects are cleaned up in a consistent manner.
        assert self._job is not None
        fn, deliver, name = self._job
        self._job = None

        # set name
        if name is not None:
            self._thread.name = name
            if set_os_thread_name:
                set_os_thread_name(self._thread.ident, name)
        result = outcome.capture(fn)

        # reset name if it was changed
        if name is not None:
            self._thread.name = self._default_name
            if set_os_thread_name:
                set_os_thread_name(self._thread.ident, self._default_name)

        # Tell the cache that we're available to be assigned a new
        # job. We do this *before* calling 'deliver', so that if
        # 'deliver' triggers a new job, it can be assigned to us
        # instead of spawning a new thread.
        self._thread_cache._idle_workers[self] = None
        try:
            deliver(result)
        except BaseException as e:
            print("Exception while delivering result of thread", file=sys.stderr)
            traceback.print_exception(type(e), e, e.__traceback__)

    def _work(self) -> None:
        while True:
            if self._worker_lock.acquire(timeout=IDLE_TIMEOUT):
                # We got a job
                self._handle_job()
            else:
                # Timeout acquiring lock, so we can probably exit. But,
                # there's a race condition: we might be assigned a job *just*
                # as we're about to exit. So we have to check.
                try:
                    del self._thread_cache._idle_workers[self]
                except KeyError:
                    # Someone else removed us from the idle worker queue, so
                    # they must be in the process of assigning us a job - loop
                    # around and wait for it.
                    continue
                else:
                    # We successfully removed ourselves from the idle
                    # worker queue, so no more jobs are incoming; it's safe to
                    # exit.
                    return


class ThreadCache:
    def __init__(self) -> None:
        self._idle_workers: dict[WorkerThread[Any], None] = {}

    def start_thread_soon(
        self,
        fn: Callable[[], RetT],
        deliver: Callable[[outcome.Outcome[RetT]], object],
        name: str | None = None,
    ) -> None:
        worker: WorkerThread[RetT]
        try:
            worker, _ = self._idle_workers.popitem()
        except KeyError:
            worker = WorkerThread(self)
        worker._job = (fn, deliver, name)
        worker._worker_lock.release()


THREAD_CACHE = ThreadCache()


def start_thread_soon(
    fn: Callable[[], RetT],
    deliver: Callable[[outcome.Outcome[RetT]], object],
    name: str | None = None,
) -> None:
    """Runs ``deliver(outcome.capture(fn))`` in a worker thread.

    Generally ``fn`` does some blocking work, and ``deliver`` delivers the
    result back to whoever is interested.

    This is a low-level, no-frills interface, very similar to using
    `threading.Thread` to spawn a thread directly. The main difference is
    that this function tries to reuse threads when possible, so it can be
    a bit faster than `threading.Thread`.

    Worker threads have the `~threading.Thread.daemon` flag set, which means
    that if your main thread exits, worker threads will automatically be
    killed. If you want to make sure that your ``fn`` runs to completion, then
    you should make sure that the main thread remains alive until ``deliver``
    is called.

    It is safe to call this function simultaneously from multiple threads.

    Args:

        fn (sync function): Performs arbitrary blocking work.

        deliver (sync function): Takes the `outcome.Outcome` of ``fn``, and
          delivers it. *Must not block.*

    Because worker threads are cached and reused for multiple calls, neither
    function should mutate thread-level state, like `threading.local` objects
    – or if they do, they should be careful to revert their changes before
    returning.

    Note:

        The split between ``fn`` and ``deliver`` serves two purposes. First,
        it's convenient, since most callers need something like this anyway.

        Second, it avoids a small race condition that could cause too many
        threads to be spawned. Consider a program that wants to run several
        jobs sequentially on a thread, so the main thread submits a job, waits
        for it to finish, submits another job, etc. In theory, this program
        should only need one worker thread. But what could happen is:

        1. Worker thread: First job finishes, and calls ``deliver``.

        2. Main thread: receives notification that the job finished, and calls
           ``start_thread_soon``.

        3. Main thread: sees that no worker threads are marked idle, so spawns
           a second worker thread.

        4. Original worker thread: marks itself as idle.

        To avoid this, threads mark themselves as idle *before* calling
        ``deliver``.

        Is this potential extra thread a major problem? Maybe not, but it's
        easy enough to avoid, and we figure that if the user is trying to
        limit how many threads they're using then it's polite to respect that.

    """
    THREAD_CACHE.start_thread_soon(fn, deliver, name)
