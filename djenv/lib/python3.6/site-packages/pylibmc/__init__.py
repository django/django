"""Snappy libmemcached wrapper

pylibmc is a Python wrapper around TangentOrg's libmemcached library.

The interface is intentionally made as close to python-memcached as possible,
so that applications can drop-in replace it.

Example usage
=============

Create a connection and configure it::

    >>> import pylibmc
    >>> m = pylibmc.Client(["10.0.0.1"], binary=True)
    >>> m.behaviors = {"tcp_nodelay": True, "ketama": True}

Nevermind this doctest shim::

    >>> from pylibmc.test import make_test_client
    >>> mc = make_test_client(behaviors=m.behaviors)

Basic operation::

    >>> mc.set("some_key", "Some value")
    True
    >>> value = mc.get("some_key")
    >>> value
    'Some value'
    >>> mc.set("another_key", 3)
    True
    >>> mc.delete("another_key")
    True
    >>> mc.set("key", b"1")  # bytes or int is fine for incrementing, str is not
    True

Atomic increments and decrements::

    >>> print(mc.incr("key"))
    2
    >>> print(mc.decr("key"))
    1

Batch operation::

    >>> mc.get_multi(["key", "another_key"]) == {'key': b'1'}
    True
    >>> mc.set_multi({"cats": ["on acid", "furry"], "dogs": True})
    []
    >>> mc.get_multi(["cats", "dogs"]) == {'cats': ['on acid', 'furry'], 'dogs': True}
    True
    >>> mc.delete_multi(["cats", "dogs", "nonextant"])
    False
    >>> mc.add_multi({"cats": ["on acid", "furry"], "dogs": True})
    []
    >>> mc.get_multi(["cats", "dogs"]) == {'cats': ['on acid', 'furry'], 'dogs': True}
    True
    >>> keys_set = mc.add_multi({"cats": "not set", "dogs": "definitely not set", "bacon": "yummy"})
    >>> set(keys_set) == set(['cats', 'dogs'])
    True
    >>> mc.get_multi(["cats", "dogs", "bacon"]) == {'cats': ['on acid', 'furry'], 'bacon': 'yummy', 'dogs': True}
    True
    >>> mc.delete_multi(["cats", "dogs", "bacon"])
    True

Further Reading
===============

See http://sendapatch.se/projects/pylibmc/
"""

import _pylibmc
from _pylibmc import *
from _pylibmc import __version__
from .consts import hashers, distributions
from .client import Client
from .pools import ClientPool, ThreadMappedPool

def build_info():
    return ("pylibmc %s for libmemcached %s (compression=%s, sasl=%s)"
            % (__version__,
               libmemcached_version,
               support_compression,
               support_sasl))

__all__ = ["hashers", "distributions", "Client",
           "ClientPool", "ThreadMappedPool"] + dir(_pylibmc)
