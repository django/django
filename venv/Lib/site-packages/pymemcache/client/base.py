# Copyright 2012 Pinterest.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import errno
import platform
import socket
from functools import partial
from ssl import SSLContext
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from pymemcache import pool
from pymemcache.exceptions import (
    MemcacheClientError,
    MemcacheIllegalInputError,
    MemcacheServerError,
    MemcacheUnexpectedCloseError,
    MemcacheUnknownCommandError,
    MemcacheUnknownError,
)
from pymemcache.serde import LegacyWrappingSerde

RECV_SIZE = 4096
VALID_STORE_RESULTS = {
    b"set": (b"STORED", b"NOT_STORED"),
    b"add": (b"STORED", b"NOT_STORED"),
    b"replace": (b"STORED", b"NOT_STORED"),
    b"append": (b"STORED", b"NOT_STORED"),
    b"prepend": (b"STORED", b"NOT_STORED"),
    b"cas": (b"STORED", b"EXISTS", b"NOT_FOUND"),
}

SOCKET_KEEPALIVE_SUPPORTED_SYSTEM = {
    "Linux",
}

STORE_RESULTS_VALUE = {
    b"STORED": True,
    b"NOT_STORED": False,
    b"NOT_FOUND": None,
    b"EXISTS": False,
}

ServerSpec = Union[Tuple[str, int], str]
Key = Union[bytes, str]


# Some of the values returned by the "stats" command
# need mapping into native Python types
def _parse_bool_int(value: bytes) -> bool:
    return int(value) != 0


def _parse_bool_string_is_yes(value: bytes) -> bool:
    return value == b"yes"


def _parse_float(value: bytes) -> float:
    return float(value.replace(b":", b"."))


def _parse_hex(value: bytes) -> int:
    return int(value, 8)


STAT_TYPES: Dict[bytes, Callable[[bytes], Any]] = {
    # General stats
    b"version": bytes,
    b"rusage_user": _parse_float,
    b"rusage_system": _parse_float,
    b"hash_is_expanding": _parse_bool_int,
    b"slab_reassign_running": _parse_bool_int,
    # Settings stats
    b"inter": bytes,
    b"growth_factor": float,
    b"stat_key_prefix": bytes,
    b"umask": _parse_hex,
    b"detail_enabled": _parse_bool_int,
    b"cas_enabled": _parse_bool_int,
    b"auth_enabled_sasl": _parse_bool_string_is_yes,
    b"maxconns_fast": _parse_bool_int,
    b"slab_reassign": _parse_bool_int,
    b"slab_automove": _parse_bool_int,
}

# Common helper functions.


def check_key_helper(
    key: Key, allow_unicode_keys: bool, key_prefix: bytes = b""
) -> bytes:
    """Checks key and add key_prefix."""
    if allow_unicode_keys:
        if isinstance(key, str):
            key = key.encode("utf8")
    elif isinstance(key, str):
        try:
            key = key.encode("ascii")
        except (UnicodeEncodeError, UnicodeDecodeError):
            raise MemcacheIllegalInputError("Non-ASCII key: %r" % key)

    key = key_prefix + key
    parts = key.split()

    if len(key) > 250:
        raise MemcacheIllegalInputError("Key is too long: %r" % key)
    # second statement catches leading or trailing whitespace
    elif len(parts) > 1 or (parts and parts[0] != key):
        raise MemcacheIllegalInputError("Key contains whitespace: %r" % key)
    elif b"\00" in key:
        raise MemcacheIllegalInputError("Key contains null: %r" % key)

    return key


def normalize_server_spec(server: ServerSpec) -> ServerSpec:
    if isinstance(server, tuple):
        return server
    if not isinstance(server, str):
        raise ValueError(f"Unsupported server specification: {server!r}")
    if server.startswith("unix:"):
        return server[5:]
    if server.startswith("/"):
        return server
    if ":" not in server or server.endswith("]"):
        host, port = server, 11211
    else:
        parts = server.rsplit(":", 1)
        host, port = parts[0], int(parts[1])
    if host.startswith("["):
        host = host.strip("[]")
    return (host, port)


class KeepaliveOpts:
    """
    A configuration structure to define the socket keepalive.

    This structure must be passed to a client. The client will configure
    its socket keepalive by using the elements of the structure.

    Args:
      idle: The time (in seconds) the connection needs to remain idle
        before TCP starts sending keepalive probes. Should be a positive
        integer most greater than zero.
      intvl: The time (in seconds) between individual keepalive probes.
        Should be a positive integer most greater than zero.
      cnt: The maximum number of keepalive probes TCP should send before
        dropping the connection. Should be a positive integer most greater
        than zero.
    """

    __slots__ = ("idle", "intvl", "cnt")

    def __init__(self, idle: int = 1, intvl: int = 1, cnt: int = 5) -> None:
        if idle < 1:
            raise ValueError("The idle parameter must be greater or equal to 1.")
        self.idle = idle
        if intvl < 1:
            raise ValueError("The intvl parameter must be greater or equal to 1.")
        self.intvl = intvl
        if cnt < 1:
            raise ValueError("The cnt parameter must be greater or equal to 1.")
        self.cnt = cnt


class Client:
    """
    A client for a single memcached server.

    *Server Connection*

     The ``server`` parameter controls how the client connects to the memcached
     server. You can either use a (host, port) tuple for a TCP connection or a
     string containing the path to a UNIX domain socket.

     The ``connect_timeout`` and ``timeout`` parameters can be used to set
     socket timeout values. By default, timeouts are disabled.

     When the ``no_delay`` flag is set, the ``TCP_NODELAY`` socket option will
     also be set. This only applies to TCP-based connections.

     Lastly, the ``socket_module`` allows you to specify an alternate socket
     implementation (such as `gevent.socket`_).

     .. _gevent.socket: http://www.gevent.org/api/gevent.socket.html

    *Keys and Values*

     Keys must have a __str__() method which should return a str with no more
     than 250 ASCII characters and no whitespace or control characters. Unicode
     strings must be encoded (as UTF-8, for example) unless they consist only
     of ASCII characters that are neither whitespace nor control characters.

     Values must have a __str__() method to convert themselves to a byte
     string. Unicode objects can be a problem since str() on a Unicode object
     will attempt to encode it as ASCII (which will fail if the value contains
     code points larger than U+127). You can fix this with a serializer or by
     just calling encode on the string (using UTF-8, for instance).

     If you intend to use anything but str as a value, it is a good idea to use
     a serializer. The pymemcache.serde library has an already implemented
     serializer which pickles and unpickles data.

    *Serialization and Deserialization*

     The constructor takes an optional object, the "serializer/deserializer"
     ("serde"), which is responsible for both serialization and deserialization
     of objects. That object must satisfy the serializer interface by providing
     two methods: `serialize` and `deserialize`. `serialize` takes two
     arguments, a key and a value, and returns a tuple of two elements, the
     serialized value, and an integer in the range 0-65535 (the "flags").
     `deserialize` takes three parameters, a key, value, and flags, and returns
     the deserialized value.

     Here is an example using JSON for non-str values:

     .. code-block:: python

         class JSONSerde(object):
             def serialize(self, key, value):
                 if isinstance(value, str):
                     return value, 1
                 return json.dumps(value), 2

             def deserialize(self, key, value, flags):
                 if flags == 1:
                     return value

                 if flags == 2:
                     return json.loads(value)

                 raise Exception("Unknown flags for value: {1}".format(flags))

    .. note::

     Most write operations allow the caller to provide a ``flags`` value to
     support advanced interaction with the server. This will **override** the
     "flags" value returned by the serializer and should therefore only be
     used when you have a complete understanding of how the value should be
     serialized, stored, and deserialized.

    *Error Handling*

     All of the methods in this class that talk to memcached can throw one of
     the following exceptions:

      * :class:`pymemcache.exceptions.MemcacheUnknownCommandError`
      * :class:`pymemcache.exceptions.MemcacheClientError`
      * :class:`pymemcache.exceptions.MemcacheServerError`
      * :class:`pymemcache.exceptions.MemcacheUnknownError`
      * :class:`pymemcache.exceptions.MemcacheUnexpectedCloseError`
      * :class:`pymemcache.exceptions.MemcacheIllegalInputError`
      * :class:`socket.timeout`
      * :class:`socket.error`

     Instances of this class maintain a persistent connection to memcached
     which is terminated when any of these exceptions are raised. The next
     call to a method on the object will result in a new connection being made
     to memcached.
    """

    def __init__(
        self,
        server: ServerSpec,
        serde=None,
        serializer=None,
        deserializer=None,
        connect_timeout: Optional[float] = None,
        timeout: Optional[float] = None,
        no_delay: bool = False,
        ignore_exc: bool = False,
        socket_module: ModuleType = socket,
        socket_keepalive: Optional[KeepaliveOpts] = None,
        key_prefix: bytes = b"",
        default_noreply: bool = True,
        allow_unicode_keys: bool = False,
        encoding: str = "ascii",
        tls_context: Optional[SSLContext] = None,
    ):
        """
        Constructor.

        Args:
          server: tuple(hostname, port) or string containing a UNIX socket path.
          serde: optional serializer object, see notes in the class docs.
          serializer: deprecated serialization function
          deserializer: deprecated deserialization function
          connect_timeout: optional float, seconds to wait for a connection to
            the memcached server. Defaults to "forever" (uses the underlying
            default socket timeout, which can be very long).
          timeout: optional float, seconds to wait for send or recv calls on
            the socket connected to memcached. Defaults to "forever" (uses the
            underlying default socket timeout, which can be very long).
          no_delay: optional bool, set the TCP_NODELAY flag, which may help
            with performance in some cases. Defaults to False.
          ignore_exc: optional bool, True to cause the "get", "gets",
            "get_many" and "gets_many" calls to treat any errors as cache
            misses. Defaults to False.
          socket_module: socket module to use, e.g. gevent.socket. Defaults to
            the standard library's socket module.
          socket_keepalive: Activate the socket keepalive feature by passing
            a KeepaliveOpts structure in this parameter. Disabled by default
            (None). This feature is only supported on Linux platforms.
          key_prefix: Prefix of key. You can use this as namespace. Defaults
            to b''.
          default_noreply: bool, the default value for 'noreply' as passed to
            store commands (except from cas, incr, and decr, which default to
            False).
          allow_unicode_keys: bool, support unicode (utf8) keys
          encoding: optional str, controls data encoding (defaults to 'ascii').

        Notes:
          The constructor does not make a connection to memcached. The first
          call to a method on the object will do that.
        """
        self.server = normalize_server_spec(server)
        self.serde = serde or LegacyWrappingSerde(serializer, deserializer)
        self.connect_timeout = connect_timeout
        self.timeout = timeout
        self.no_delay = no_delay
        self.ignore_exc = ignore_exc
        self.socket_module = socket_module
        self.socket_keepalive = socket_keepalive
        user_system = platform.system()
        if self.socket_keepalive is not None:
            if user_system not in SOCKET_KEEPALIVE_SUPPORTED_SYSTEM:
                raise SystemError(
                    "Pymemcache's socket keepalive mechanism doesn't "
                    "support your system ({user_system}). If "
                    "you see this message it mean that you tried to "
                    "configure your socket keepalive on an unsupported "
                    "system. To fix the problem pass `socket_"
                    "keepalive=False` or use a supported system. "
                    "Supported systems are: {systems}".format(
                        user_system=user_system,
                        systems=", ".join(sorted(SOCKET_KEEPALIVE_SUPPORTED_SYSTEM)),
                    )
                )
            if not isinstance(self.socket_keepalive, KeepaliveOpts):
                raise ValueError(
                    "Unsupported keepalive options. If you see this message "
                    "it means that you passed an unsupported object within "
                    "the param `socket_keepalive`. To fix it "
                    "please instantiate and pass to socket_keepalive a "
                    "KeepaliveOpts object. That's the only supported type "
                    "of structure."
                )
        self.sock: Optional[socket.socket] = None
        if isinstance(key_prefix, str):
            key_prefix = key_prefix.encode("ascii")
        if not isinstance(key_prefix, bytes):
            raise TypeError("key_prefix should be bytes.")
        self.key_prefix = key_prefix
        self.default_noreply = default_noreply
        self.allow_unicode_keys = allow_unicode_keys
        self.encoding = encoding
        self.tls_context = tls_context

    def check_key(self, key: Key, key_prefix: bytes) -> bytes:
        """Checks key and add key_prefix."""
        return check_key_helper(
            key, allow_unicode_keys=self.allow_unicode_keys, key_prefix=key_prefix
        )

    def _connect(self) -> None:
        self.close()

        s = self.socket_module

        if not isinstance(self.server, tuple):
            sockaddr = self.server
            sock = s.socket(s.AF_UNIX, s.SOCK_STREAM)
        else:
            sock = None
            error = None
            host, port = self.server
            info = s.getaddrinfo(host, port, s.AF_UNSPEC, s.SOCK_STREAM, s.IPPROTO_TCP)
            for family, socktype, proto, _, sockaddr in info:
                try:
                    sock = s.socket(family, socktype, proto)
                    if self.no_delay:
                        sock.setsockopt(s.IPPROTO_TCP, s.TCP_NODELAY, 1)
                    if self.tls_context:
                        context = self.tls_context
                        sock = context.wrap_socket(sock, server_hostname=host)
                except Exception as e:
                    error = e
                    if sock is not None:
                        sock.close()
                        sock = None
                else:
                    break

            if error is not None:
                raise error

        try:
            sock.settimeout(self.connect_timeout)
            if self.socket_keepalive is not None:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                sock.setsockopt(
                    socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, self.socket_keepalive.idle
                )
                sock.setsockopt(
                    socket.IPPROTO_TCP,
                    socket.TCP_KEEPINTVL,
                    self.socket_keepalive.intvl,
                )
                sock.setsockopt(
                    socket.IPPROTO_TCP, socket.TCP_KEEPCNT, self.socket_keepalive.cnt
                )
            sock.connect(sockaddr)
            sock.settimeout(self.timeout)
        except Exception:
            sock.close()
            raise

        self.sock = sock

    def close(self) -> None:
        """Close the connection to memcached, if it is open. The next call to a
        method that requires a connection will re-open it."""
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            finally:
                self.sock = None

    disconnect_all = close

    def set(
        self,
        key: Key,
        value: Any,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> Optional[bool]:
        """
        The memcached "set" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).
          flags: optional int, arbitrary bit field used for server-specific
                flags

        Returns:
          If no exception is raised, always returns True. If an exception is
          raised, the set may or may not have occurred. If noreply is True,
          then a successful return does not guarantee a successful set.
        """
        if noreply is None:
            noreply = self.default_noreply
        # Optional because _store_cmd lookup in STORE_RESULTS_VALUE can return None in some cases.
        # TODO: refactor to fix
        return self._store_cmd(b"set", {key: value}, expire, noreply, flags=flags)[key]

    def set_many(
        self,
        values: Dict[Key, Any],
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> List[Key]:
        """
        A convenience function for setting multiple values.

        Args:
          values: dict(str, str), a dict of keys and values, see class docs
                  for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).
          flags: optional int, arbitrary bit field used for server-specific
                 flags

        Returns:
          Returns a list of keys that failed to be inserted.
          If noreply is True, always returns empty list.
        """
        if noreply is None:
            noreply = self.default_noreply
        result = self._store_cmd(b"set", values, expire, noreply, flags=flags)
        return [k for k, v in result.items() if not v]

    set_multi = set_many

    def add(
        self,
        key: Key,
        value: Any,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool:
        """
        The memcached "add" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).
          flags: optional int, arbitrary bit field used for server-specific
                  flags

        Returns:
          If ``noreply`` is True (or if it is unset and ``self.default_noreply``
          is True), the return value is always True. Otherwise the return value
          is True if the value was stored, and False if it was not (because
          the key already existed).
        """
        if noreply is None:
            noreply = self.default_noreply
        response = self._store_cmd(b"add", {key: value}, expire, noreply, flags=flags)[
            key
        ]
        # For typing, can only be None, if cas command
        assert response is not None
        return response

    def replace(
        self,
        key: Key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool:
        """
        The memcached "replace" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).
          flags: optional int, arbitrary bit field used for server-specific
                flags

        Returns:
          If ``noreply`` is True (or if it is unset and ``self.default_noreply``
          is True), the return value is always True. Otherwise returns True if
          the value was stored and False if it wasn't (because the key didn't
          already exist).
        """
        if noreply is None:
            noreply = self.default_noreply
        response = self._store_cmd(
            b"replace", {key: value}, expire, noreply, flags=flags
        )[key]
        # for typing
        assert response is not None
        return response

    def append(
        self,
        key: Key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ) -> bool:
        """
        The memcached "append" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).
          flags: optional int, arbitrary bit field used for server-specific
                flags

        Returns:
          True.
        """
        if noreply is None:
            noreply = self.default_noreply
        response = self._store_cmd(
            b"append", {key: value}, expire, noreply, flags=flags
        )[key]
        # For typing
        assert response is not None
        return response

    def prepend(
        self,
        key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        """
        The memcached "prepend" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).
          flags: optional int, arbitrary bit field used for server-specific
                flags

        Returns:
          True.
        """
        if noreply is None:
            noreply = self.default_noreply
        return self._store_cmd(b"prepend", {key: value}, expire, noreply, flags=flags)[
            key
        ]

    def cas(
        self,
        key,
        value,
        cas,
        expire: int = 0,
        noreply=False,
        flags: Optional[int] = None,
    ) -> Optional[bool]:
        """
        The memcached "cas" command.

        Args:
          key: str, see class docs for details.
          value: str, see class docs for details.
          cas: int or str that only contains the characters '0'-'9'.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, False to wait for the reply (the default).
          flags: optional int, arbitrary bit field used for server-specific
                flags

        Returns:
          If ``noreply`` is True (or if it is unset and ``self.default_noreply``
          is True), the return value is always True. Otherwise returns None if
          the key didn't exist, False if it existed but had a different cas
          value and True if it existed and was changed.
        """
        cas = self._check_cas(cas)
        return self._store_cmd(
            b"cas", {key: value}, expire, noreply, flags=flags, cas=cas
        )[key]

    def get(self, key: Key, default: Optional[Any] = None) -> Any:
        """
        The memcached "get" command, but only for one key, as a convenience.

        Args:
          key: str, see class docs for details.
          default: value that will be returned if the key was not found.

        Returns:
          The value for the key, or default if the key wasn't found.
        """
        return self._fetch_cmd(b"get", [key], False, key_prefix=self.key_prefix).get(
            key, default
        )

    def get_many(self, keys: Iterable[Key]) -> Dict[Key, Any]:
        """
        The memcached "get" command.

        Args:
          keys: list(str), see class docs for details.

        Returns:
          A dict in which the keys are elements of the "keys" argument list
          and the values are values from the cache. The dict may contain all,
          some or none of the given keys.
        """
        if not keys:
            return {}

        return self._fetch_cmd(b"get", keys, False, key_prefix=self.key_prefix)

    get_multi = get_many

    def gets(
        self, key: Key, default: Any = None, cas_default: Any = None
    ) -> Tuple[Any, Any]:
        """
        The memcached "gets" command for one key, as a convenience.

        Args:
          key: str, see class docs for details.
          default: value that will be returned if the key was not found.
          cas_default: same behaviour as default argument.

        Returns:
          A tuple of (value, cas)
          or (default, cas_defaults) if the key was not found.
        """
        defaults = (default, cas_default)
        return self._fetch_cmd(b"gets", [key], True, key_prefix=self.key_prefix).get(
            key, defaults
        )

    def gets_many(self, keys: Iterable[Key]) -> Dict[Key, Tuple[Any, Any]]:
        """
        The memcached "gets" command.

        Args:
          keys: list(str), see class docs for details.

        Returns:
          A dict in which the keys are elements of the "keys" argument list and
          the values are tuples of (value, cas) from the cache. The dict may
          contain all, some or none of the given keys.
        """
        if not keys:
            return {}

        return self._fetch_cmd(b"gets", keys, True, key_prefix=self.key_prefix)

    def delete(self, key: Key, noreply: Optional[bool] = None) -> bool:
        """
        The memcached "delete" command.

        Args:
          key: str, see class docs for details.
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).

        Returns:
          If ``noreply`` is True (or if it is unset and ``self.default_noreply``
          is True), the return value is always True. Otherwise returns True if
          the key was deleted, and False if it wasn't found.
        """
        if noreply is None:
            noreply = self.default_noreply
        cmd = b"delete " + self.check_key(key, self.key_prefix)
        if noreply:
            cmd += b" noreply"
        cmd += b"\r\n"
        results = self._misc_cmd([cmd], b"delete", noreply)
        if noreply:
            return True
        return results[0] == b"DELETED"

    def delete_many(self, keys: Iterable[Key], noreply: Optional[bool] = None) -> bool:
        """
        A convenience function to delete multiple keys.

        Args:
          keys: list(str), the list of keys to delete.
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).

        Returns:
          True. If an exception is raised then all, some or none of the keys
          may have been deleted. Otherwise all the keys have been sent to
          memcache for deletion and if noreply is False, they have been
          acknowledged by memcache.
        """
        if not keys:
            return True

        if noreply is None:
            noreply = self.default_noreply

        cmds = []
        for key in keys:
            cmds.append(
                b"delete "
                + self.check_key(key, self.key_prefix)
                + (b" noreply" if noreply else b"")
                + b"\r\n"
            )
        self._misc_cmd(cmds, b"delete", noreply)
        return True

    delete_multi = delete_many

    def incr(
        self, key: Key, value: int, noreply: Optional[bool] = False
    ) -> Optional[int]:
        """
        The memcached "incr" command.

        Args:
          key: str, see class docs for details.
          value: int, the amount by which to increment the value.
          noreply: optional bool, False to wait for the reply (the default).

        Returns:
          If noreply is True, always returns None. Otherwise returns the new
          value of the key, or None if the key wasn't found.
        """
        key = self.check_key(key, self.key_prefix)
        val = self._check_integer(value, "value")
        cmd = b"incr " + key + b" " + val
        if noreply:
            cmd += b" noreply"
        cmd += b"\r\n"
        results = self._misc_cmd([cmd], b"incr", noreply)
        if noreply:
            return None
        if results[0] == b"NOT_FOUND":
            return None
        return int(results[0])

    def decr(
        self, key: Key, value: int, noreply: Optional[bool] = False
    ) -> Optional[int]:
        """
        The memcached "decr" command.

        Args:
          key: str, see class docs for details.
          value: int, the amount by which to decrement the value.
          noreply: optional bool, False to wait for the reply (the default).

        Returns:
          If noreply is True, always returns None. Otherwise returns the new
          value of the key, or None if the key wasn't found.
        """
        key = self.check_key(key, self.key_prefix)
        val = self._check_integer(value, "value")
        cmd = b"decr " + key + b" " + val
        if noreply:
            cmd += b" noreply"
        cmd += b"\r\n"
        results = self._misc_cmd([cmd], b"decr", noreply)
        if noreply:
            return None
        if results[0] == b"NOT_FOUND":
            return None
        return int(results[0])

    def touch(self, key: Key, expire: int = 0, noreply: Optional[bool] = None) -> bool:
        """
        The memcached "touch" command.

        Args:
          key: str, see class docs for details.
          expire: optional int, number of seconds until the item is expired
                  from the cache, or zero for no expiry (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).

        Returns:
          True if the expiration time was updated, False if the key wasn't
          found.
        """
        if noreply is None:
            noreply = self.default_noreply
        key = self.check_key(key, self.key_prefix)
        expire_bytes = self._check_integer(expire, "expire")
        cmd = b"touch " + key + b" " + expire_bytes
        if noreply:
            cmd += b" noreply"
        cmd += b"\r\n"
        results = self._misc_cmd([cmd], b"touch", noreply)
        if noreply:
            return True
        return results[0] == b"TOUCHED"

    def stats(self, *args):
        """
        The memcached "stats" command.

        The returned keys depend on what the "stats" command returns.
        A best effort is made to convert values to appropriate Python
        types, defaulting to strings when a conversion cannot be made.

        Args:
          *arg: extra string arguments to the "stats" command. See the
                memcached protocol documentation for more information.

        Returns:
          A dict of the returned stats.
        """
        result = self._fetch_cmd(b"stats", args, False)

        for key, value in result.items():
            converter = STAT_TYPES.get(key, int)
            try:
                result[key] = converter(value)
            except Exception:
                pass

        return result

    def cache_memlimit(self, memlimit) -> bool:
        """
        The memcached "cache_memlimit" command.

        Args:
          memlimit: int, the number of megabytes to set as the new cache memory
                    limit.

        Returns:
          If no exception is raised, always returns True.
        """
        memlimit = self._check_integer(memlimit, "memlimit")
        self._fetch_cmd(b"cache_memlimit", [memlimit], False)
        return True

    def version(self) -> bytes:
        """
        The memcached "version" command.

        Returns:
            A string of the memcached version.
        """
        cmd = b"version\r\n"
        results = self._misc_cmd([cmd], b"version", False)
        before, _, after = results[0].partition(b" ")

        if before != b"VERSION":
            raise MemcacheUnknownError(f"Received unexpected response: {results[0]!r}")
        return after

    def raw_command(
        self, command: Union[str, bytes], end_tokens: Union[str, bytes] = "\r\n"
    ) -> bytes:
        """
        Sends an arbitrary command to the server and parses the response until a
        specified token is encountered.

        Args:
            command: str|bytes: The command to send.
            end_tokens: str|bytes: The token expected at the end of the
                response. If the `end_token` is not found, the client will wait
                until the timeout specified in the constructor.

        Returns:
            The response from the server, with the `end_token` removed.
        """
        encoding = "utf8" if self.allow_unicode_keys else "ascii"
        command = command.encode(encoding) if isinstance(command, str) else command
        end_tokens = (
            end_tokens.encode(encoding) if isinstance(end_tokens, str) else end_tokens
        )
        return self._misc_cmd([b"" + command + b"\r\n"], command, False, end_tokens)[0]

    def flush_all(self, delay: int = 0, noreply: Optional[bool] = None) -> bool:
        """
        The memcached "flush_all" command.

        Args:
          delay: optional int, the number of seconds to wait before flushing,
                 or zero to flush immediately (the default).
          noreply: optional bool, True to not wait for the reply (defaults to
                   self.default_noreply).

        Returns:
          True.
        """
        if noreply is None:
            noreply = self.default_noreply
        delay_bytes = self._check_integer(delay, "delay")
        cmd = b"flush_all " + delay_bytes
        if noreply:
            cmd += b" noreply"
        cmd += b"\r\n"
        results = self._misc_cmd([cmd], b"flush_all", noreply)
        if noreply:
            return True
        return results[0] == b"OK"

    def quit(self) -> None:
        """
        The memcached "quit" command.

        This will close the connection with memcached. Calling any other
        method on this object will re-open the connection, so this object can
        be re-used after quit.
        """
        cmd = b"quit\r\n"
        self._misc_cmd([cmd], b"quit", True)
        self.close()

    def shutdown(self, graceful: bool = False) -> None:
        """
        The memcached "shutdown" command.

        This will request shutdown and eventual termination of the server,
        optionally preceded by a graceful stop of memcached's internal state
        machine. Note that the server needs to have been started with the
        shutdown protocol command enabled with the --enable-shutdown flag.

        Args:
          graceful: optional bool, True to request a graceful shutdown with
                    SIGUSR1 (defaults to False, i.e. SIGINT shutdown).
        """
        cmd = b"shutdown"
        if graceful:
            cmd += b" graceful"
        cmd += b"\r\n"

        # The shutdown command raises a server-side error if the shutdown
        # protocol command is not enabled. Otherwise, a successful shutdown
        # is expected to close the remote end of the transport.
        try:
            self._misc_cmd([cmd], b"shutdown", False)
        except MemcacheUnexpectedCloseError:
            pass

    def _raise_errors(self, line: bytes, name: bytes) -> None:
        if line.startswith(b"ERROR"):
            raise MemcacheUnknownCommandError(name)

        if line.startswith(b"CLIENT_ERROR"):
            error = line[line.find(b" ") + 1 :]
            raise MemcacheClientError(error)

        if line.startswith(b"SERVER_ERROR"):
            error = line[line.find(b" ") + 1 :]
            raise MemcacheServerError(error)

    def _check_integer(self, value: int, name: str) -> bytes:
        """Check that a value is an integer and encode it as a binary string"""
        if not isinstance(value, int):
            raise MemcacheIllegalInputError(
                f"{name} must be integer, got bad value: {value!r}"
            )

        return str(value).encode(self.encoding)

    def _check_cas(self, cas: Union[int, str, bytes]) -> bytes:
        """Check that a value is a valid input for 'cas' -- either an int or a
        string containing only 0-9

        The value will be (re)encoded so that we can accept strings or bytes.
        """
        # convert non-binary values to binary
        if isinstance(cas, (int, str)):
            try:
                cas = str(cas).encode(self.encoding)
            except UnicodeEncodeError:
                raise MemcacheIllegalInputError("non-ASCII cas value: %r" % cas)
        elif not isinstance(cas, bytes):
            raise MemcacheIllegalInputError(
                "cas must be integer, string, or bytes, got bad value: %r" % cas
            )

        if not cas.isdigit():
            raise MemcacheIllegalInputError(
                "cas must only contain values in 0-9, got bad value: %r" % cas
            )

        return cas

    def _extract_value(
        self,
        expect_cas: bool,
        line: bytes,
        buf: bytes,
        remapped_keys: Dict[bytes, Key],
        prefixed_keys: List[bytes],
    ) -> Tuple[Key, Union[Any, Tuple[Any, bytes]], bytes]:
        """
        This function is abstracted from _fetch_cmd to support different ways
        of value extraction. In order to use this feature, _extract_value needs
        to be overridden in the subclass.
        """
        if expect_cas:
            _, key, flags, size, cas = line.split()
        else:
            try:
                _, key, flags, size = line.split()
            except Exception as e:
                raise ValueError(f"Unable to parse line {line!r}: {e}")

        value = None
        try:
            # For typing
            assert self.sock is not None

            buf, value = _readvalue(self.sock, buf, int(size))
        except MemcacheUnexpectedCloseError:
            self.close()
            raise
        original_key = remapped_keys[key]
        value = self.serde.deserialize(original_key, value, int(flags))

        if expect_cas:
            return original_key, (value, cas), buf
        else:
            return original_key, value, buf

    def _fetch_cmd(
        self,
        name: bytes,
        keys: Iterable[Key],
        expect_cas: bool,
        key_prefix: bytes = b"",
    ) -> Dict[Key, Any]:
        prefixed_keys = [self.check_key(k, key_prefix=key_prefix) for k in keys]
        remapped_keys = dict(zip(prefixed_keys, keys))

        # It is important for all keys to be listed in their original order.
        cmd = name
        if prefixed_keys:
            cmd += b" " + b" ".join(prefixed_keys)
        cmd += b"\r\n"

        try:
            if self.sock is None:
                self._connect()

                # For typing
                assert self.sock is not None

            self.sock.sendall(cmd)

            buf = b""
            line = None
            result: Dict[Key, Any] = {}
            while True:
                try:
                    buf, line = _readline(self.sock, buf)
                except MemcacheUnexpectedCloseError:
                    self.close()
                    raise
                self._raise_errors(line, name)
                if line == b"END" or line == b"OK":
                    return result
                elif line.startswith(b"VALUE"):
                    key, value, buf = self._extract_value(
                        expect_cas, line, buf, remapped_keys, prefixed_keys
                    )
                    result[key] = value
                elif name == b"stats" and line.startswith(b"STAT"):
                    key_value = line.split()
                    result[key_value[1]] = key_value[2] if len(key_value) > 2 else b""
                elif name == b"stats" and line.startswith(b"ITEM"):
                    # For 'stats cachedump' commands
                    key_value = line.split()
                    result[key_value[1]] = b" ".join(key_value[2:])
                else:
                    raise MemcacheUnknownError(line[:32])
        except Exception:
            self.close()
            if self.ignore_exc:
                return {}
            raise

    def _store_cmd(
        self,
        name: bytes,
        values: Dict[Key, Any],
        expire: int,
        noreply: bool,
        flags: Optional[int] = None,
        cas: Optional[bytes] = None,
    ) -> Dict[Key, Optional[bool]]:
        cmds = []
        keys = []

        extra = b""
        if cas is not None:
            extra += b" " + cas
        if noreply:
            extra += b" noreply"
        expire_bytes = self._check_integer(expire, "expire")

        for key, data in values.items():
            # must be able to reliably map responses back to the original order
            keys.append(key)

            key = self.check_key(key, self.key_prefix)
            data, data_flags = self.serde.serialize(key, data)

            # If 'flags' was explicitly provided, it overrides the value
            # returned by the serializer.
            if flags is not None:
                data_flags = flags

            if not isinstance(data, bytes):
                try:
                    data = str(data).encode(self.encoding)
                except UnicodeEncodeError as e:
                    raise MemcacheIllegalInputError(
                        "Data values must be binary-safe: %s" % e
                    )

            cmds.append(
                name
                + b" "
                + key
                + b" "
                + str(data_flags).encode(self.encoding)
                + b" "
                + expire_bytes
                + b" "
                + str(len(data)).encode(self.encoding)
                + extra
                + b"\r\n"
                + data
                + b"\r\n"
            )

        if self.sock is None:
            self._connect()

            # For typing
            assert self.sock is not None

        try:
            self.sock.sendall(b"".join(cmds))
            if noreply:
                return {k: True for k in keys}

            results = {}
            buf = b""
            line = None
            for key in keys:
                try:
                    buf, line = _readline(self.sock, buf)
                except MemcacheUnexpectedCloseError:
                    self.close()
                    raise
                self._raise_errors(line, name)

                if line in VALID_STORE_RESULTS[name]:
                    results[key] = STORE_RESULTS_VALUE[line]
                else:
                    raise MemcacheUnknownError(line[:32])
            return results
        except Exception:
            self.close()
            raise

    def _misc_cmd(
        self,
        cmds: Iterable[bytes],
        cmd_name: bytes,
        noreply: Optional[bool],
        end_tokens=None,
    ) -> List[bytes]:

        # If no end_tokens have been given, just assume standard memcached
        # operations, which end in "\r\n", use regular code for that.
        _reader: Callable[[socket.socket, bytes], Tuple[bytes, bytes]]
        if end_tokens:
            _reader = partial(_readsegment, end_tokens=end_tokens)
        else:
            _reader = _readline

        if self.sock is None:
            self._connect()

            # For typing
            assert self.sock is not None

        try:
            self.sock.sendall(b"".join(cmds))

            if noreply:
                return []

            results = []
            buf = b""
            line = None
            for cmd in cmds:
                try:
                    buf, line = _reader(self.sock, buf)
                except MemcacheUnexpectedCloseError:
                    self.close()
                    raise
                self._raise_errors(line, cmd_name)
                results.append(line)
            return results

        except Exception:
            self.close()
            raise

    def __setitem__(self, key: Key, value):
        self.set(key, value, noreply=True)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError
        return value

    def __delitem__(self, key):
        self.delete(key, noreply=True)


class PooledClient:
    """A thread-safe pool of clients (with the same client api).

    Args:
      max_pool_size: maximum pool size to use (going above this amount
                     triggers a runtime error), by default this is 2147483648L
                     when not provided (or none).
      pool_idle_timeout: pooled connections are discarded if they have been
                         unused for this many seconds. A value of 0 indicates
                         that pooled connections are never discarded.
      lock_generator: a callback/type that takes no arguments that will
                      be called to create a lock or semaphore that can
                      protect the pool from concurrent access (for example a
                      eventlet lock or semaphore could be used instead)

    Further arguments are interpreted as for :py:class:`.Client` constructor.

    Note: if `serde` is given, the same object will be used for *all* clients
    in the pool. Your serde object must therefore be thread-safe.
    """

    #: :class:`Client` class used to create new clients
    client_class = Client

    def __init__(
        self,
        server: ServerSpec,
        serde=None,
        serializer=None,
        deserializer=None,
        connect_timeout=None,
        timeout=None,
        no_delay=False,
        ignore_exc=False,
        socket_module=socket,
        socket_keepalive=None,
        key_prefix=b"",
        max_pool_size=None,
        pool_idle_timeout=0,
        lock_generator=None,
        default_noreply: bool = True,
        allow_unicode_keys=False,
        encoding="ascii",
        tls_context=None,
    ):
        self.server = normalize_server_spec(server)
        self.serde = serde or LegacyWrappingSerde(serializer, deserializer)
        self.connect_timeout = connect_timeout
        self.timeout = timeout
        self.no_delay = no_delay
        self.ignore_exc = ignore_exc
        self.socket_module = socket_module
        self.socket_keepalive = socket_keepalive
        self.default_noreply = default_noreply
        self.allow_unicode_keys = allow_unicode_keys
        if isinstance(key_prefix, str):
            key_prefix = key_prefix.encode("ascii")
        if not isinstance(key_prefix, bytes):
            raise TypeError("key_prefix should be bytes.")
        self.key_prefix = key_prefix
        self.client_pool = pool.ObjectPool(
            self._create_client,
            after_remove=lambda client: client.close(),
            max_size=max_pool_size,
            idle_timeout=pool_idle_timeout,
            lock_generator=lock_generator,
        )
        self.encoding = encoding
        self.tls_context = tls_context

    def check_key(self, key: Key) -> bytes:
        """Checks key and add key_prefix."""
        return check_key_helper(
            key, allow_unicode_keys=self.allow_unicode_keys, key_prefix=self.key_prefix
        )

    def _create_client(self) -> Client:
        return self.client_class(
            self.server,
            serde=self.serde,
            connect_timeout=self.connect_timeout,
            timeout=self.timeout,
            no_delay=self.no_delay,
            # We need to know when it fails *always* so that we
            # can remove/destroy it from the pool...
            ignore_exc=False,
            socket_module=self.socket_module,
            socket_keepalive=self.socket_keepalive,
            key_prefix=self.key_prefix,
            default_noreply=self.default_noreply,
            allow_unicode_keys=self.allow_unicode_keys,
            tls_context=self.tls_context,
        )

    def close(self) -> None:
        self.client_pool.clear()

    disconnect_all = close

    def set(
        self,
        key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.set(key, value, expire=expire, noreply=noreply, flags=flags)

    def set_many(
        self,
        values,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.set_many(values, expire=expire, noreply=noreply, flags=flags)

    set_multi = set_many

    def replace(
        self,
        key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.replace(
                key, value, expire=expire, noreply=noreply, flags=flags
            )

    def append(
        self,
        key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.append(
                key, value, expire=expire, noreply=noreply, flags=flags
            )

    def prepend(
        self,
        key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.prepend(
                key, value, expire=expire, noreply=noreply, flags=flags
            )

    def cas(
        self,
        key,
        value,
        cas,
        expire: int = 0,
        noreply=False,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.cas(
                key, value, cas, expire=expire, noreply=noreply, flags=flags
            )

    def get(self, key: Key, default: Any = None) -> Any:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            try:
                return client.get(key, default)
            except Exception:
                if self.ignore_exc:
                    return default
                else:
                    raise

    def get_many(self, keys: Iterable[Key]) -> Dict[Key, Any]:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            try:
                return client.get_many(keys)
            except Exception:
                if self.ignore_exc:
                    return {}
                else:
                    raise

    get_multi = get_many

    def gets(self, key: Key) -> Tuple[Any, Any]:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            try:
                return client.gets(key)
            except Exception:
                if self.ignore_exc:
                    return (None, None)
                else:
                    raise

    def gets_many(self, keys: Iterable[Key]) -> Dict[Key, Tuple[Any, Any]]:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            try:
                return client.gets_many(keys)
            except Exception:
                if self.ignore_exc:
                    return {}
                else:
                    raise

    def delete(self, key: Key, noreply: Optional[bool] = None) -> bool:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.delete(key, noreply=noreply)

    def delete_many(self, keys: Iterable[Key], noreply: Optional[bool] = None) -> bool:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.delete_many(keys, noreply=noreply)

    delete_multi = delete_many

    def add(
        self,
        key: Key,
        value,
        expire: int = 0,
        noreply: Optional[bool] = None,
        flags: Optional[int] = None,
    ):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.add(key, value, expire=expire, noreply=noreply, flags=flags)

    def incr(self, key: Key, value, noreply=False):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.incr(key, value, noreply=noreply)

    def decr(self, key: Key, value, noreply=False):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.decr(key, value, noreply=noreply)

    def touch(self, key: Key, expire: int = 0, noreply=None):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.touch(key, expire=expire, noreply=noreply)

    def stats(self, *args):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            try:
                return client.stats(*args)
            except Exception:
                if self.ignore_exc:
                    return {}
                else:
                    raise

    def version(self) -> bytes:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.version()

    def flush_all(self, delay=0, noreply=None) -> bool:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.flush_all(delay=delay, noreply=noreply)

    def quit(self) -> None:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            try:
                client.quit()
            finally:
                self.client_pool.destroy(client)

    def shutdown(self, graceful: bool = False) -> None:
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            client.shutdown(graceful)

    def raw_command(self, command, end_tokens=b"\r\n"):
        with self.client_pool.get_and_release(destroy_on_fail=True) as client:
            return client.raw_command(command, end_tokens)

    def __setitem__(self, key: Key, value):
        self.set(key, value, noreply=True)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError
        return value

    def __delitem__(self, key):
        self.delete(key, noreply=True)


def _readline(sock: socket.socket, buf: bytes) -> Tuple[bytes, bytes]:
    """Read line of text from the socket.

    Read a line of text (delimited by "\r\n") from the socket, and
    return that line along with any trailing characters read from the
    socket.

    Args:
        sock: Socket object, should be connected.
        buf: Bytes, zero or more characters, returned from an earlier
            call to _readline or _readvalue (pass an empty byte string on the
            first call).

    Returns:
      A tuple of (buf, line) where line is the full line read from the
      socket (minus the "\r\n" characters) and buf is any trailing
      characters read after the "\r\n" was found (which may be an empty
      byte string).

    """
    chunks: List[bytes] = []
    last_char = b""

    while True:
        # We're reading in chunks, so "\r\n" could appear in one chunk,
        # or across the boundary of two chunks, so we check for both
        # cases.

        # This case must appear first, since the buffer could have
        # later \r\n characters in it and we want to get the first \r\n.
        if last_char == b"\r" and buf[0:1] == b"\n":
            # Strip the last character from the last chunk.
            chunks[-1] = chunks[-1][:-1]
            return buf[1:], b"".join(chunks)
        else:
            token_pos = buf.find(b"\r\n")
            if token_pos != -1:
                # Note: 2 == len(b"\r\n")
                before, after = buf[:token_pos], buf[token_pos + 2 :]
                chunks.append(before)
                return after, b"".join(chunks)

        if buf:
            chunks.append(buf)
            last_char = buf[-1:]

        buf = _recv(sock, RECV_SIZE)
        if not buf:
            raise MemcacheUnexpectedCloseError()


def _readvalue(sock: socket.socket, buf: bytes, size: int):
    """Read specified amount of bytes from the socket.

    Read size bytes, followed by the "\r\n" characters, from the socket,
    and return those bytes and any trailing bytes read after the "\r\n".

    Args:
        sock: Socket object, should be connected.
        buf: String, zero or more characters, returned from an earlier
            call to _readline or _readvalue (pass an empty string on the
            first call).
        size: Integer, number of bytes to read from the socket.

    Returns:
      A tuple of (buf, value) where value is the bytes read from the
      socket (there will be exactly size bytes) and buf is trailing
      characters read after the "\r\n" following the bytes (but not
      including the \r\n).

    """
    chunks = []
    rlen = size + 2
    while rlen - len(buf) > 0:
        if buf:
            rlen -= len(buf)
            chunks.append(buf)
        buf = _recv(sock, RECV_SIZE)
        if not buf:
            raise MemcacheUnexpectedCloseError()

    # Now we need to remove the \r\n from the end. There are two cases we care
    # about: the \r\n is all in the last buffer, or only the \n is in the last
    # buffer, and we need to remove the \r from the penultimate buffer.

    if rlen == 1:
        # replace the last chunk with the same string minus the last character,
        # which is always '\r' in this case.
        chunks[-1] = chunks[-1][:-1]
    else:
        # Just remove the "\r\n" from the latest chunk
        chunks.append(buf[: rlen - 2])

    return buf[rlen:], b"".join(chunks)


def _readsegment(
    sock: socket.socket, buf: bytes, end_tokens: bytes
) -> Tuple[bytes, bytes]:
    """Read a segment from the socket.

    Read a segment from the socket, up to the first end_token sub-string/bytes,
    and return that segment.

    Args:
        sock: Socket object, should be connected.
        buf: bytes, zero or more bytes, returned from an earlier
            call to _readline, _readsegment or _readvalue (pass an empty
            byte-string on the first call).
        end_tokens: bytes, indicates the end of the segment, generally this is
            b"\\r\\n" for memcached.

    Returns:
      A tuple of (buf, line) where line is the full line read from the
      socket (minus the end_tokens bytes) and buf is any trailing
      characters read after the end_tokens was found (which may be an empty
      bytes object).

    """
    result = bytes()

    while True:

        tokens_pos = buf.find(end_tokens)
        if tokens_pos != -1:
            before, after = buf[:tokens_pos], buf[tokens_pos + len(end_tokens) :]
            result += before
            return after, result

        buf = _recv(sock, RECV_SIZE)
        if not buf:
            raise MemcacheUnexpectedCloseError()


def _recv(sock: socket.socket, size: int) -> bytes:
    """sock.recv() with retry on EINTR"""
    while True:
        try:
            return sock.recv(size)
        except OSError as e:
            if e.errno != errno.EINTR:
                raise
