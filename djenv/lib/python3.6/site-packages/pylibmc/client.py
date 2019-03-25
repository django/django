"""Python-level wrapper client"""

import _pylibmc
from .consts import (hashers, distributions, all_behaviors,
                     hashers_rvs, distributions_rvs,
                     all_callbacks, BehaviorDict)

_all_behaviors_set = set(all_behaviors)
_all_behaviors_set.update(set(all_callbacks))

server_type_map = {"tcp":   _pylibmc.server_type_tcp,
                   "udp":   _pylibmc.server_type_udp,
                   "unix":  _pylibmc.server_type_unix}

_MISS_SENTINEL = object()

def _split_spec_type(spec):
    if spec.startswith("/"):
        return ("unix", spec)
    else:
        if spec.startswith("udp:"):
            return ("udp", spec[4:])
        else:
            return ("tcp", spec)

def _unpack_addr(spec, port=None, weight=1):
    if spec.startswith("["):
        if "]" not in spec:
            raise ValueError(spec)
        if spec.endswith("]"):
            addr = spec[1:-1]
        else:
            (addr, port) = spec[1:].rsplit("]:", 1)
    elif ":" in spec:
        (addr, port) = spec.split(":", 1)
    else:
        addr = spec

    if isinstance(port, str) and ":" in port:
        (port, weight) = port.split(":", 1)
    return (addr, port, weight)

def translate_server_spec(server, port=11211, weight=1):
    """Translate/normalize specification *server* into 4-tuple (scheme, addr, port, weight).

    This is format is used by the extension module.

    >>> translate_server_spec("127.0.0.1")
    (1, '127.0.0.1', 11211, 1)
    >>> translate_server_spec("udp:127.0.0.1")
    (2, '127.0.0.1', 11211, 1)
    >>> translate_server_spec("/var/run/memcached.sock")
    (4, '/var/run/memcached.sock', 0, 1)
    >>> translate_server_spec("/var/run/memcached.sock", weight=2)
    (4, '/var/run/memcached.sock', 0, 2)

    >>> translate_server_spec("127.0.0.1:22122")
    (1, '127.0.0.1', 22122, 1)
    >>> translate_server_spec("127.0.0.1:1234:2")
    (1, '127.0.0.1', 1234, 2)
    >>> translate_server_spec("127.0.0.1", port=1234, weight=2)
    (1, '127.0.0.1', 1234, 2)

    >>> translate_server_spec("[::1]:22122")
    (1, '::1', 22122, 1)
    >>> translate_server_spec("[::1]")
    (1, '::1', 11211, 1)
    >>> translate_server_spec("[::1]:22122:3")
    (1, '::1', 22122, 3)
    """
    (scheme, spec) = _split_spec_type(server)
    stype = server_type_map[scheme]
    if scheme == "unix":
        (addr, port) = (spec, 0)
    elif scheme in ("tcp", "udp"):
        (addr, port, weight) = _unpack_addr(spec, port=port, weight=weight)
    return (stype, str(addr), int(port), int(weight))

def translate_server_specs(servers):
    addr_tups = []
    for server in servers:
        # Anti-pattern for convenience
        if isinstance(server, tuple) and len(server) == 3:
            addr_tup = server
        else:
            addr_tup = translate_server_spec(server)
        addr_tups.append(addr_tup)
    return addr_tups

def _behaviors_symbolic(behaviors):
    """Turn numeric constants into symbolic strings"""

    behaviors = behaviors.copy()

    behaviors["hash"] = hashers_rvs[behaviors["hash"]]
    behaviors["distribution"] = distributions_rvs[behaviors["distribution"]]

    return behaviors

def _behaviors_numeric(behaviors):
    """Inverse function of behaviors_symbolic"""

    if not behaviors:
        return behaviors

    behaviors = behaviors.copy()

    if "_retry_timeout" in behaviors:
        behaviors.setdefault("retry_timeout", behaviors.pop("_retry_timeout"))

    unknown = set(behaviors).difference(_all_behaviors_set)
    if unknown:
        names = ", ".join(map(str, sorted(unknown)))
        raise ValueError("unknown behavior names: %s" % (names,))

    if behaviors.get("hash") is not None:
        behaviors["hash"] = hashers[behaviors["hash"]]
    if behaviors.get("ketama_hash") in hashers:
        behaviors["ketama_hash"] = hashers[behaviors["ketama_hash"]]
    if behaviors.get("distribution") is not None:
        behaviors["distribution"] = distributions[behaviors["distribution"]]

    return behaviors

class Client(_pylibmc.client):
    def __init__(self, servers, behaviors=None, binary=False,
                 username=None, password=None):
        """Initialize a memcached client instance.

        This connects to the servers in *servers*, which will default to being
        TCP servers. If it looks like a filesystem path, a UNIX socket. If
        prefixed with `udp:`, a UDP connection.

        If *binary* is True, the binary memcached protocol is used.

        SASL authentication is supported if libmemcached supports it (check
        *pylibmc.support_sasl*). Requires both username and password.
        Note that SASL requires *binary*=True.
        """
        self.binary = binary
        self.addresses = list(servers)
        super(Client, self).__init__(servers=translate_server_specs(servers),
                                     binary=binary,
                                     username=username, password=password,
                                     behaviors=_behaviors_numeric(behaviors))

    def __repr__(self):
        return "%s(%r, binary=%r)" % (self.__class__.__name__,
                                      self.addresses, self.binary)

    def __str__(self):
        addrs = ", ".join(map(str, self.addresses))
        return "<%s for %s, binary=%r>" % (self.__class__.__name__,
                                           addrs, self.binary)

    # {{{ Mapping interface
    def __getitem__(self, key):
        value = self.get(key, _MISS_SENTINEL)
        if value is _MISS_SENTINEL:
            raise KeyError(key)
        else:
            return value

    def __setitem__(self, key, value):
        if not self.set(key, value):
            raise KeyError("failed setting %r" % (key,))

    def __delitem__(self, key):
        if not self.delete(key):
            raise KeyError(key)

    def __contains__(self, key):
        return self.get(key, _MISS_SENTINEL) is not _MISS_SENTINEL
    # }}}

    # {{{ Behaviors
    def get_behaviors(self):
        """Gets the behaviors from the underlying C client instance.

        Reverses the integer constants for `hash` and `distribution` into more
        understandable string values. See *set_behaviors* for info.
        """
        return BehaviorDict(self, _behaviors_symbolic(super(Client, self).get_behaviors()))

    def set_behaviors(self, behaviors):
        """Sets the behaviors on the underlying C client instance.

        Takes care of morphing the `hash` key, if specified, into the
        corresponding integer constant (which the C client expects.) If,
        however, an unknown value is specified, it's passed on to the C client
        (where it most surely will error out.)

        This also happens for `distribution`.

        Translates old underscored behavior names to new ones for API leniency.
        """
        return super(Client, self).set_behaviors(_behaviors_numeric(behaviors))

    behaviors = property(get_behaviors, set_behaviors)
    @property
    def behaviours(self):
        raise AttributeError("nobody uses british spellings")
    # }}}

    def clone(self):
        obj = super(Client, self).clone()
        obj.addresses = list(self.addresses)
        obj.binary = self.binary
        return obj

if __name__ == "__main__":
    import doctest
    doctest.testmod()
