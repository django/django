"""Pooling"""

from __future__ import with_statement
from contextlib import contextmanager

try:
    import threading
except ImportError:
    import dummy_threading as threading

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

class ClientPool(Queue):
    """Client pooling helper.

    This is mostly useful in threaded environments, because a client isn't
    thread-safe at all. Instead, what you want to do is have each thread use
    its own client, but you don't want to reconnect these all the time.

    The solution is a pool, and this class is a helper for that.

    >>> from pylibmc.test import make_test_client
    >>> mc = make_test_client()
    >>> pool = ClientPool()
    >>> pool.fill(mc, 4)
    >>> with pool.reserve() as mc:
    ...     mc.set("hi", "ho")
    ...     mc.delete("hi")
    ... 
    True
    True
    """

    def __init__(self, mc=None, n_slots=0):
        Queue.__init__(self, n_slots)
        if mc and n_slots:
            self.fill(mc, n_slots)

    @contextmanager
    def reserve(self, block=False):
        """Context manager for reserving a client from the pool.

        If *block* is given and the pool is exhausted, the pool waits for
        another thread to fill it before returning.
        """
        mc = self.get(block)
        try:
            yield mc
        finally:
            self.put(mc)

    def fill(self, mc, n_slots):
        """Fill *n_slots* of the pool with clones of *mc*."""
        for i in range(n_slots):
            self.put(mc.clone())

class ThreadMappedPool(dict):
    """Much like the *ClientPool*, helps you with pooling.

    In a threaded environment, you'd most likely want to have a client per
    thread. And there'd be no harm in one thread keeping the same client at all
    times. So, why not map threads to clients? That's what this class does.

    If a client is reserved, this class checks for a key based on the current
    thread, and if none exists, clones the master client and inserts that key.

    Of course this requires that you let the pool know when a thread is done
    with its reserved instance, so therefore ``relinquish`` must be called
    before thread exit.

    >>> from pylibmc.test import make_test_client
    >>> mc = make_test_client()
    >>> pool = ThreadMappedPool(mc)
    >>> with pool.reserve() as mc:
    ...     mc.set("hi", "ho")
    ...     mc.delete("hi")
    ... 
    True
    True
    """

    def __new__(cls, master):
        return super(ThreadMappedPool, cls).__new__(cls)

    def __init__(self, master):
        self.master = master

    @property
    def current_key(self):
        return threading.current_thread().ident

    @contextmanager
    def reserve(self):
        """Reserve a client.

        Creates a new client based on the master client if none exists for the
        current thread.
        """
        key = self.current_key
        mc = self.pop(key, None)
        if mc is None:
            mc = self.master.clone()
        try:
            yield mc
        finally:
            self[key] = mc

    def relinquish(self):
        """Relinquish any reserved client for the current context.

        Call this method before exiting a thread if it might potentially use
        this pool.
        """
        return self.pop(self.current_key, None)
