from __future__ import annotations

import os
import select
import socket as _stdlib_socket
import sys
from operator import index
from socket import AddressFamily, SocketKind
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Literal,
    SupportsIndex,
    TypeVar,
    Union,
    overload,
)

import idna as _idna

import trio
from trio._util import wraps as _wraps

from . import _core

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    from typing_extensions import Buffer, Concatenate, ParamSpec, Self, TypeAlias

    from ._abc import HostnameResolver, SocketFactory

    P = ParamSpec("P")


T = TypeVar("T")

# _stdlib_socket.socket supports 13 different socket families, see
# https://docs.python.org/3/library/socket.html#socket-families
# and the return type of several methods in SocketType will depend on those. Typeshed
# has ended up typing those return types as `Any` in most cases, but for users that
# know which family/families they're working in we could make SocketType a generic type,
# where you specify the return values you expect from those methods depending on the
# protocol the socket will be handling.
# But without the ability to default the value to `Any` it will be overly cumbersome for
# most users, so currently we just specify it as `Any`. Otherwise we would write:
# `AddressFormat = TypeVar("AddressFormat")`
# but instead we simply do:
AddressFormat: TypeAlias = Any


# Usage:
#
#   async with _try_sync():
#       return sync_call_that_might_fail_with_exception()
#   # we only get here if the sync call in fact did fail with a
#   # BlockingIOError
#   return await do_it_properly_with_a_check_point()
#
class _try_sync:
    def __init__(
        self, blocking_exc_override: Callable[[BaseException], bool] | None = None
    ):
        self._blocking_exc_override = blocking_exc_override

    def _is_blocking_io_error(self, exc: BaseException) -> bool:
        if self._blocking_exc_override is None:
            return isinstance(exc, BlockingIOError)
        else:
            return self._blocking_exc_override(exc)

    async def __aenter__(self) -> None:
        await trio.lowlevel.checkpoint_if_cancelled()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc_value is not None and self._is_blocking_io_error(exc_value):
            # Discard the exception and fall through to the code below the
            # block
            return True
        else:
            await trio.lowlevel.cancel_shielded_checkpoint()
            # Let the return or exception propagate
            return False


################################################################
# Overrides
################################################################

_resolver: _core.RunVar[HostnameResolver | None] = _core.RunVar("hostname_resolver")
_socket_factory: _core.RunVar[SocketFactory | None] = _core.RunVar("socket_factory")


def set_custom_hostname_resolver(
    hostname_resolver: HostnameResolver | None,
) -> HostnameResolver | None:
    """Set a custom hostname resolver.

    By default, Trio's :func:`getaddrinfo` and :func:`getnameinfo` functions
    use the standard system resolver functions. This function allows you to
    customize that behavior. The main intended use case is for testing, but it
    might also be useful for using third-party resolvers like `c-ares
    <https://c-ares.haxx.se/>`__ (though be warned that these rarely make
    perfect drop-in replacements for the system resolver). See
    :class:`trio.abc.HostnameResolver` for more details.

    Setting a custom hostname resolver affects all future calls to
    :func:`getaddrinfo` and :func:`getnameinfo` within the enclosing call to
    :func:`trio.run`. All other hostname resolution in Trio is implemented in
    terms of these functions.

    Generally you should call this function just once, right at the beginning
    of your program.

    Args:
      hostname_resolver (trio.abc.HostnameResolver or None): The new custom
          hostname resolver, or None to restore the default behavior.

    Returns:
      The previous hostname resolver (which may be None).

    """
    old = _resolver.get(None)
    _resolver.set(hostname_resolver)
    return old


def set_custom_socket_factory(
    socket_factory: SocketFactory | None,
) -> SocketFactory | None:
    """Set a custom socket object factory.

    This function allows you to replace Trio's normal socket class with a
    custom class. This is very useful for testing, and probably a bad idea in
    any other circumstance. See :class:`trio.abc.HostnameResolver` for more
    details.

    Setting a custom socket factory affects all future calls to :func:`socket`
    within the enclosing call to :func:`trio.run`.

    Generally you should call this function just once, right at the beginning
    of your program.

    Args:
      socket_factory (trio.abc.SocketFactory or None): The new custom
          socket factory, or None to restore the default behavior.

    Returns:
      The previous socket factory (which may be None).

    """
    old = _socket_factory.get(None)
    _socket_factory.set(socket_factory)
    return old


################################################################
# getaddrinfo and friends
################################################################

_NUMERIC_ONLY = _stdlib_socket.AI_NUMERICHOST | _stdlib_socket.AI_NUMERICSERV


# It would be possible to @overload the return value depending on Literal[AddressFamily.INET/6], but should probably be added in typeshed first
async def getaddrinfo(
    host: bytes | str | None,
    port: bytes | str | int | None,
    family: int = 0,
    type: int = 0,
    proto: int = 0,
    flags: int = 0,
) -> list[
    tuple[
        AddressFamily, SocketKind, int, str, tuple[str, int] | tuple[str, int, int, int]
    ]
]:
    """Look up a numeric address given a name.

    Arguments and return values are identical to :func:`socket.getaddrinfo`,
    except that this version is async.

    Also, :func:`trio.socket.getaddrinfo` correctly uses IDNA 2008 to process
    non-ASCII domain names. (:func:`socket.getaddrinfo` uses IDNA 2003, which
    can give the wrong result in some cases and cause you to connect to a
    different host than the one you intended; see `bpo-17305
    <https://bugs.python.org/issue17305>`__.)

    This function's behavior can be customized using
    :func:`set_custom_hostname_resolver`.

    """

    # If host and port are numeric, then getaddrinfo doesn't block and we can
    # skip the whole thread thing, which seems worthwhile. So we try first
    # with the _NUMERIC_ONLY flags set, and then only spawn a thread if that
    # fails with EAI_NONAME:
    def numeric_only_failure(exc: BaseException) -> bool:
        return (
            isinstance(exc, _stdlib_socket.gaierror)
            and exc.errno == _stdlib_socket.EAI_NONAME
        )

    async with _try_sync(numeric_only_failure):
        return _stdlib_socket.getaddrinfo(
            host, port, family, type, proto, flags | _NUMERIC_ONLY
        )
    # That failed; it's a real hostname. We better use a thread.
    #
    # Also, it might be a unicode hostname, in which case we want to do our
    # own encoding using the idna module, rather than letting Python do
    # it. (Python will use the old IDNA 2003 standard, and possibly get the
    # wrong answer - see bpo-17305). However, the idna module is picky, and
    # will refuse to process some valid hostname strings, like "::1". So if
    # it's already ascii, we pass it through; otherwise, we encode it to.
    if isinstance(host, str):
        try:
            host = host.encode("ascii")
        except UnicodeEncodeError:
            # UTS-46 defines various normalizations; in particular, by default
            # idna.encode will error out if the hostname has Capital Letters
            # in it; with uts46=True it will lowercase them instead.
            host = _idna.encode(host, uts46=True)
    hr = _resolver.get(None)
    if hr is not None:
        return await hr.getaddrinfo(host, port, family, type, proto, flags)
    else:
        return await trio.to_thread.run_sync(
            _stdlib_socket.getaddrinfo,
            host,
            port,
            family,
            type,
            proto,
            flags,
            abandon_on_cancel=True,
        )


async def getnameinfo(
    sockaddr: tuple[str, int] | tuple[str, int, int, int], flags: int
) -> tuple[str, str]:
    """Look up a name given a numeric address.

    Arguments and return values are identical to :func:`socket.getnameinfo`,
    except that this version is async.

    This function's behavior can be customized using
    :func:`set_custom_hostname_resolver`.

    """
    hr = _resolver.get(None)
    if hr is not None:
        return await hr.getnameinfo(sockaddr, flags)
    else:
        return await trio.to_thread.run_sync(
            _stdlib_socket.getnameinfo, sockaddr, flags, abandon_on_cancel=True
        )


async def getprotobyname(name: str) -> int:
    """Look up a protocol number by name. (Rarely used.)

    Like :func:`socket.getprotobyname`, but async.

    """
    return await trio.to_thread.run_sync(
        _stdlib_socket.getprotobyname, name, abandon_on_cancel=True
    )


# obsolete gethostbyname etc. intentionally omitted
# likewise for create_connection (use open_tcp_stream instead)

################################################################
# Socket "constructors"
################################################################


def from_stdlib_socket(sock: _stdlib_socket.socket) -> SocketType:
    """Convert a standard library :class:`socket.socket` object into a Trio
    socket object.

    """
    return _SocketType(sock)


@_wraps(_stdlib_socket.fromfd, assigned=(), updated=())
def fromfd(
    fd: SupportsIndex,
    family: AddressFamily | int = _stdlib_socket.AF_INET,
    type: SocketKind | int = _stdlib_socket.SOCK_STREAM,
    proto: int = 0,
) -> SocketType:
    """Like :func:`socket.fromfd`, but returns a Trio socket object."""
    family, type_, proto = _sniff_sockopts_for_fileno(family, type, proto, index(fd))
    return from_stdlib_socket(_stdlib_socket.fromfd(fd, family, type_, proto))


if sys.platform == "win32" or (
    not TYPE_CHECKING and hasattr(_stdlib_socket, "fromshare")
):

    @_wraps(_stdlib_socket.fromshare, assigned=(), updated=())
    def fromshare(info: bytes) -> SocketType:
        """Like :func:`socket.fromshare`, but returns a Trio socket object."""
        return from_stdlib_socket(_stdlib_socket.fromshare(info))


if sys.platform == "win32":
    FamilyT: TypeAlias = int
    TypeT: TypeAlias = int
    FamilyDefault = _stdlib_socket.AF_INET
else:
    FamilyDefault: Literal[None] = None
    FamilyT: TypeAlias = Union[int, AddressFamily, None]
    TypeT: TypeAlias = Union[_stdlib_socket.socket, int]


@_wraps(_stdlib_socket.socketpair, assigned=(), updated=())
def socketpair(
    family: FamilyT = FamilyDefault,
    type: TypeT = SocketKind.SOCK_STREAM,
    proto: int = 0,
) -> tuple[SocketType, SocketType]:
    """Like :func:`socket.socketpair`, but returns a pair of Trio socket
    objects.

    """
    left, right = _stdlib_socket.socketpair(family, type, proto)
    return (from_stdlib_socket(left), from_stdlib_socket(right))


@_wraps(_stdlib_socket.socket, assigned=(), updated=())
def socket(
    family: AddressFamily | int = _stdlib_socket.AF_INET,
    type: SocketKind | int = _stdlib_socket.SOCK_STREAM,
    proto: int = 0,
    fileno: int | None = None,
) -> SocketType:
    """Create a new Trio socket, like :class:`socket.socket`.

    This function's behavior can be customized using
    :func:`set_custom_socket_factory`.

    """
    if fileno is None:
        sf = _socket_factory.get(None)
        if sf is not None:
            return sf.socket(family, type, proto)
    else:
        family, type, proto = _sniff_sockopts_for_fileno(  # noqa: A001
            family, type, proto, fileno
        )
    stdlib_socket = _stdlib_socket.socket(family, type, proto, fileno)
    return from_stdlib_socket(stdlib_socket)


def _sniff_sockopts_for_fileno(
    family: AddressFamily | int,
    type_: SocketKind | int,
    proto: int,
    fileno: int | None,
) -> tuple[AddressFamily | int, SocketKind | int, int]:
    """Correct SOCKOPTS for given fileno, falling back to provided values."""
    # Wrap the raw fileno into a Python socket object
    # This object might have the wrong metadata, but it lets us easily call getsockopt
    # and then we'll throw it away and construct a new one with the correct metadata.
    if sys.platform != "linux":
        return family, type_, proto
    from socket import (  # type: ignore[attr-defined]
        SO_DOMAIN,
        SO_PROTOCOL,
        SO_TYPE,
        SOL_SOCKET,
    )

    sockobj = _stdlib_socket.socket(family, type_, proto, fileno=fileno)
    try:
        family = sockobj.getsockopt(SOL_SOCKET, SO_DOMAIN)
        proto = sockobj.getsockopt(SOL_SOCKET, SO_PROTOCOL)
        type_ = sockobj.getsockopt(SOL_SOCKET, SO_TYPE)
    finally:
        # Unwrap it again, so that sockobj.__del__ doesn't try to close our socket
        sockobj.detach()
    return family, type_, proto


################################################################
# SocketType
################################################################

# sock.type gets weird stuff set in it, in particular on Linux:
#
#   https://bugs.python.org/issue21327
#
# But on other platforms (e.g. Windows) SOCK_NONBLOCK and SOCK_CLOEXEC aren't
# even defined. To recover the actual socket type (e.g. SOCK_STREAM) from a
# socket.type attribute, mask with this:
_SOCK_TYPE_MASK = ~(
    getattr(_stdlib_socket, "SOCK_NONBLOCK", 0)
    | getattr(_stdlib_socket, "SOCK_CLOEXEC", 0)
)


def _make_simple_sock_method_wrapper(
    fn: Callable[Concatenate[_stdlib_socket.socket, P], T],
    wait_fn: Callable[[_stdlib_socket.socket], Awaitable[None]],
    maybe_avail: bool = False,
) -> Callable[Concatenate[_SocketType, P], Awaitable[T]]:
    @_wraps(fn, assigned=("__name__",), updated=())
    async def wrapper(self: _SocketType, *args: P.args, **kwargs: P.kwargs) -> T:
        return await self._nonblocking_helper(wait_fn, fn, *args, **kwargs)

    wrapper.__doc__ = f"""Like :meth:`socket.socket.{fn.__name__}`, but async.

            """
    if maybe_avail:
        wrapper.__doc__ += (
            f"Only available on platforms where :meth:`socket.socket.{fn.__name__}` is "
            "available."
        )
    return wrapper


# Helpers to work with the (hostname, port) language that Python uses for socket
# addresses everywhere. Split out into a standalone function so it can be reused by
# FakeNet.


# Take an address in Python's representation, and returns a new address in
# the same representation, but with names resolved to numbers,
# etc.
#
# local=True means that the address is being used with bind() or similar
# local=False means that the address is being used with connect() or sendto() or
# similar.
#


# Using a TypeVar to indicate we return the same type of address appears to give errors
# when passed a union of address types.
# @overload likely works, but is extremely verbose.
# NOTE: this function does not always checkpoint
async def _resolve_address_nocp(
    type_: int,
    family: AddressFamily,
    proto: int,
    *,
    ipv6_v6only: bool | int,
    address: AddressFormat,
    local: bool,
) -> Any:
    # Do some pre-checking (or exit early for non-IP sockets)
    if family == _stdlib_socket.AF_INET:
        if not isinstance(address, tuple) or not len(address) == 2:
            raise ValueError("address should be a (host, port) tuple")
    elif family == _stdlib_socket.AF_INET6:
        if not isinstance(address, tuple) or not 2 <= len(address) <= 4:
            raise ValueError(
                "address should be a (host, port, [flowinfo, [scopeid]]) tuple"
            )
    elif hasattr(_stdlib_socket, "AF_UNIX") and family == _stdlib_socket.AF_UNIX:
        # unwrap path-likes
        assert isinstance(address, (str, bytes))
        return os.fspath(address)
    else:
        return address

    # -- From here on we know we have IPv4 or IPV6 --
    host: str | None
    host, port, *_ = address
    # Fast path for the simple case: already-resolved IP address,
    # already-resolved port. This is particularly important for UDP, since
    # every sendto call goes through here.
    if isinstance(port, int) and host is not None:
        try:
            _stdlib_socket.inet_pton(family, host)
        except (OSError, TypeError):
            pass
        else:
            return address
    # Special cases to match the stdlib, see gh-277
    if host == "":
        host = None
    if host == "<broadcast>":
        host = "255.255.255.255"
    flags = 0
    if local:
        flags |= _stdlib_socket.AI_PASSIVE
    # Since we always pass in an explicit family here, AI_ADDRCONFIG
    # doesn't add any value -- if we have no ipv6 connectivity and are
    # working with an ipv6 socket, then things will break soon enough! And
    # if we do enable it, then it makes it impossible to even run tests
    # for ipv6 address resolution on travis-ci, which as of 2017-03-07 has
    # no ipv6.
    # flags |= AI_ADDRCONFIG
    if family == _stdlib_socket.AF_INET6 and not ipv6_v6only:
        flags |= _stdlib_socket.AI_V4MAPPED
    gai_res = await getaddrinfo(host, port, family, type_, proto, flags)
    # AFAICT from the spec it's not possible for getaddrinfo to return an
    # empty list.
    assert len(gai_res) >= 1
    # Address is the last item in the first entry
    (*_, normed), *_ = gai_res
    # The above ignored any flowid and scopeid in the passed-in address,
    # so restore them if present:
    if family == _stdlib_socket.AF_INET6:
        list_normed = list(normed)
        assert len(normed) == 4
        if len(address) >= 3:
            list_normed[2] = address[2]
        if len(address) >= 4:
            list_normed[3] = address[3]
        return tuple(list_normed)
    return normed


class SocketType:
    def __init__(self) -> None:
        # make sure this __init__ works with multiple inheritance
        super().__init__()
        # and only raises error if it's directly constructed
        if type(self) == SocketType:
            raise TypeError(
                "SocketType is an abstract class; use trio.socket.socket if you "
                "want to construct a socket object"
            )

    def detach(self) -> int:
        raise NotImplementedError

    def fileno(self) -> int:
        raise NotImplementedError

    def getpeername(self) -> AddressFormat:
        raise NotImplementedError

    def getsockname(self) -> AddressFormat:
        raise NotImplementedError

    @overload
    def getsockopt(self, /, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, /, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self, /, level: int, optname: int, buflen: int | None = None
    ) -> int | bytes:
        raise NotImplementedError

    @overload
    def setsockopt(self, /, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self, /, level: int, optname: int, value: None, optlen: int
    ) -> None: ...

    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        raise NotImplementedError

    def listen(self, /, backlog: int = min(_stdlib_socket.SOMAXCONN, 128)) -> None:
        raise NotImplementedError

    def get_inheritable(self) -> bool:
        raise NotImplementedError

    def set_inheritable(self, inheritable: bool) -> None:
        raise NotImplementedError

    if sys.platform == "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "share")
    ):

        def share(self, /, process_id: int) -> bytes:
            raise NotImplementedError

    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @property
    def family(self) -> AddressFamily:
        raise NotImplementedError

    @property
    def type(self) -> SocketKind:
        raise NotImplementedError

    @property
    def proto(self) -> int:
        raise NotImplementedError

    @property
    def did_shutdown_SHUT_WR(self) -> bool:
        """Return True if the socket has been shut down with the SHUT_WR flag"""
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def dup(self) -> SocketType:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    async def bind(self, address: AddressFormat) -> None:
        raise NotImplementedError

    def shutdown(self, flag: int) -> None:
        raise NotImplementedError

    def is_readable(self) -> bool:
        """Return True if the socket is readable. This is checked with `select.select` on Windows, otherwise `select.poll`."""
        raise NotImplementedError

    async def wait_writable(self) -> None:
        """Convenience method that calls trio.lowlevel.wait_writable for the object."""
        raise NotImplementedError

    async def accept(self) -> tuple[SocketType, AddressFormat]:
        raise NotImplementedError

    async def connect(self, address: AddressFormat) -> None:
        raise NotImplementedError

    # argument names with __ used because of typeshed, see comment for recv in _SocketType
    def recv(__self, __buflen: int, __flags: int = 0) -> Awaitable[bytes]:
        raise NotImplementedError

    def recv_into(
        __self, buffer: Buffer, nbytes: int = 0, flags: int = 0
    ) -> Awaitable[int]:
        raise NotImplementedError

    # return type of socket.socket.recvfrom in typeshed is tuple[bytes, Any]
    def recvfrom(
        __self, __bufsize: int, __flags: int = 0
    ) -> Awaitable[tuple[bytes, AddressFormat]]:
        raise NotImplementedError

    # return type of socket.socket.recvfrom_into in typeshed is tuple[bytes, Any]
    def recvfrom_into(
        __self, buffer: Buffer, nbytes: int = 0, flags: int = 0
    ) -> Awaitable[tuple[int, AddressFormat]]:
        raise NotImplementedError

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg")
    ):

        def recvmsg(
            __self,
            __bufsize: int,
            __ancbufsize: int = 0,
            __flags: int = 0,
        ) -> Awaitable[tuple[bytes, list[tuple[int, int, bytes]], int, Any]]:
            raise NotImplementedError

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg_into")
    ):

        def recvmsg_into(
            __self,
            __buffers: Iterable[Buffer],
            __ancbufsize: int = 0,
            __flags: int = 0,
        ) -> Awaitable[tuple[int, list[tuple[int, int, bytes]], int, Any]]:
            raise NotImplementedError

    def send(__self, __bytes: Buffer, __flags: int = 0) -> Awaitable[int]:
        raise NotImplementedError

    @overload
    async def sendto(
        self, __data: Buffer, __address: tuple[object, ...] | str | Buffer
    ) -> int: ...

    @overload
    async def sendto(
        self,
        __data: Buffer,
        __flags: int,
        __address: tuple[object, ...] | str | Buffer,
    ) -> int: ...

    async def sendto(self, *args: Any) -> int:
        raise NotImplementedError

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "sendmsg")
    ):

        @_wraps(_stdlib_socket.socket.sendmsg, assigned=(), updated=())
        async def sendmsg(
            self,
            __buffers: Iterable[Buffer],
            __ancdata: Iterable[tuple[int, int, Buffer]] = (),
            __flags: int = 0,
            __address: AddressFormat | None = None,
        ) -> int:
            raise NotImplementedError


# copy docstrings from socket.SocketType / socket.socket
for name, obj in SocketType.__dict__.items():
    # skip dunders and already defined docstrings
    if name.startswith("__") or obj.__doc__:
        continue
    # try both socket.socket and socket.SocketType
    for stdlib_type in _stdlib_socket.socket, _stdlib_socket.SocketType:
        stdlib_obj = getattr(stdlib_type, name, None)
        if stdlib_obj and stdlib_obj.__doc__:
            break
    else:
        continue
    obj.__doc__ = stdlib_obj.__doc__


class _SocketType(SocketType):
    def __init__(self, sock: _stdlib_socket.socket):
        if type(sock) is not _stdlib_socket.socket:
            # For example, ssl.SSLSocket subclasses socket.socket, but we
            # certainly don't want to blindly wrap one of those.
            raise TypeError(
                f"expected object of type 'socket.socket', not '{type(sock).__name__}'"
            )
        self._sock = sock
        self._sock.setblocking(False)
        self._did_shutdown_SHUT_WR = False

    ################################################################
    # Simple + portable methods and attributes
    ################################################################

    # forwarded methods
    def detach(self) -> int:
        return self._sock.detach()

    def fileno(self) -> int:
        return self._sock.fileno()

    def getpeername(self) -> AddressFormat:
        return self._sock.getpeername()

    def getsockname(self) -> AddressFormat:
        return self._sock.getsockname()

    @overload
    def getsockopt(self, /, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, /, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self, /, level: int, optname: int, buflen: int | None = None
    ) -> int | bytes:
        if buflen is None:
            return self._sock.getsockopt(level, optname)
        return self._sock.getsockopt(level, optname, buflen)

    @overload
    def setsockopt(self, /, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self, /, level: int, optname: int, value: None, optlen: int
    ) -> None: ...

    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        if optlen is None:
            if value is None:
                raise TypeError(
                    "invalid value for argument 'value', must not be None when specifying optlen"
                )
            return self._sock.setsockopt(level, optname, value)
        if value is not None:
            raise TypeError(
                f"invalid value for argument 'value': {value!r}, must be None when specifying optlen"
            )

        # Note: PyPy may crash here due to setsockopt only supporting
        # four parameters.
        return self._sock.setsockopt(level, optname, value, optlen)

    def listen(self, /, backlog: int = min(_stdlib_socket.SOMAXCONN, 128)) -> None:
        return self._sock.listen(backlog)

    def get_inheritable(self) -> bool:
        return self._sock.get_inheritable()

    def set_inheritable(self, inheritable: bool) -> None:
        return self._sock.set_inheritable(inheritable)

    if sys.platform == "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "share")
    ):

        def share(self, /, process_id: int) -> bytes:
            return self._sock.share(process_id)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return self._sock.__exit__(exc_type, exc_value, traceback)

    @property
    def family(self) -> AddressFamily:
        return self._sock.family

    @property
    def type(self) -> SocketKind:
        return self._sock.type

    @property
    def proto(self) -> int:
        return self._sock.proto

    @property
    def did_shutdown_SHUT_WR(self) -> bool:
        return self._did_shutdown_SHUT_WR

    def __repr__(self) -> str:
        return repr(self._sock).replace("socket.socket", "trio.socket.socket")

    def dup(self) -> SocketType:
        """Same as :meth:`socket.socket.dup`."""
        return _SocketType(self._sock.dup())

    def close(self) -> None:
        if self._sock.fileno() != -1:
            trio.lowlevel.notify_closing(self._sock)
            self._sock.close()

    async def bind(self, address: AddressFormat) -> None:
        address = await self._resolve_address_nocp(address, local=True)
        if (
            hasattr(_stdlib_socket, "AF_UNIX")
            and self.family == _stdlib_socket.AF_UNIX
            and address[0]
        ):
            # Use a thread for the filesystem traversal (unless it's an
            # abstract domain socket)
            return await trio.to_thread.run_sync(self._sock.bind, address)
        else:
            # POSIX actually says that bind can return EWOULDBLOCK and
            # complete asynchronously, like connect. But in practice AFAICT
            # there aren't yet any real systems that do this, so we'll worry
            # about it when it happens.
            await trio.lowlevel.checkpoint()
            return self._sock.bind(address)

    def shutdown(self, flag: int) -> None:
        # no need to worry about return value b/c always returns None:
        self._sock.shutdown(flag)
        # only do this if the call succeeded:
        if flag in [_stdlib_socket.SHUT_WR, _stdlib_socket.SHUT_RDWR]:
            self._did_shutdown_SHUT_WR = True

    def is_readable(self) -> bool:
        # use select.select on Windows, and select.poll everywhere else
        if sys.platform == "win32":
            rready, _, _ = select.select([self._sock], [], [], 0)
            return bool(rready)
        p = select.poll()
        p.register(self._sock, select.POLLIN)
        return bool(p.poll(0))

    async def wait_writable(self) -> None:
        await _core.wait_writable(self._sock)

    async def _resolve_address_nocp(
        self,
        address: AddressFormat,
        *,
        local: bool,
    ) -> AddressFormat:
        if self.family == _stdlib_socket.AF_INET6:
            ipv6_v6only = self._sock.getsockopt(
                _stdlib_socket.IPPROTO_IPV6, _stdlib_socket.IPV6_V6ONLY
            )
        else:
            ipv6_v6only = False
        return await _resolve_address_nocp(
            self.type,
            self.family,
            self.proto,
            ipv6_v6only=ipv6_v6only,
            address=address,
            local=local,
        )

    # args and kwargs must be starred, otherwise pyright complains:
    # '"args" member of ParamSpec is valid only when used with *args parameter'
    # '"kwargs" member of ParamSpec is valid only when used with **kwargs parameter'
    # wait_fn and fn must also be first in the signature
    # 'Keyword parameter cannot appear in signature after ParamSpec args parameter'

    async def _nonblocking_helper(
        self,
        wait_fn: Callable[[_stdlib_socket.socket], Awaitable[None]],
        fn: Callable[Concatenate[_stdlib_socket.socket, P], T],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> T:
        # We have to reconcile two conflicting goals:
        # - We want to make it look like we always blocked in doing these
        #   operations. The obvious way is to always do an IO wait before
        #   calling the function.
        # - But, we also want to provide the correct semantics, and part
        #   of that means giving correct errors. So, for example, if you
        #   haven't called .listen(), then .accept() raises an error
        #   immediately. But in this same circumstance, then on macOS, the
        #   socket does not register as readable. So if we block waiting
        #   for read *before* we call accept, then we'll be waiting
        #   forever instead of properly raising an error. (On Linux,
        #   interestingly, AFAICT a socket that can't possible read/write
        #   *does* count as readable/writable for select() purposes. But
        #   not on macOS.)
        #
        # So, we have to call the function once, with the appropriate
        # cancellation/yielding sandwich if it succeeds, and if it gives
        # BlockingIOError *then* we fall back to IO wait.
        #
        # XX think if this can be combined with the similar logic for IOCP
        # submission...
        async with _try_sync():
            return fn(self._sock, *args, **kwargs)
        # First attempt raised BlockingIOError:
        while True:
            await wait_fn(self._sock)
            try:
                return fn(self._sock, *args, **kwargs)
            except BlockingIOError:
                pass

    ################################################################
    # accept
    ################################################################

    _accept = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.accept, _core.wait_readable
    )

    async def accept(self) -> tuple[SocketType, AddressFormat]:
        """Like :meth:`socket.socket.accept`, but async."""
        sock, addr = await self._accept()
        return from_stdlib_socket(sock), addr

    ################################################################
    # connect
    ################################################################

    async def connect(self, address: AddressFormat) -> None:
        # nonblocking connect is weird -- you call it to start things
        # off, then the socket becomes writable as a completion
        # notification. This means it isn't really cancellable... we close the
        # socket if cancelled, to avoid confusion.
        try:
            address = await self._resolve_address_nocp(address, local=False)
            async with _try_sync():
                # An interesting puzzle: can a non-blocking connect() return EINTR
                # (= raise InterruptedError)? PEP 475 specifically left this as
                # the one place where it lets an InterruptedError escape instead
                # of automatically retrying. This is based on the idea that EINTR
                # from connect means that the connection was already started, and
                # will continue in the background. For a blocking connect, this
                # sort of makes sense: if it returns EINTR then the connection
                # attempt is continuing in the background, and on many system you
                # can't then call connect() again because there is already a
                # connect happening. See:
                #
                #   http://www.madore.org/~david/computers/connect-intr.html
                #
                # For a non-blocking connect, it doesn't make as much sense --
                # surely the interrupt didn't happen after we successfully
                # initiated the connect and are just waiting for it to complete,
                # because a non-blocking connect does not wait! And the spec
                # describes the interaction between EINTR/blocking connect, but
                # doesn't have anything useful to say about non-blocking connect:
                #
                #   http://pubs.opengroup.org/onlinepubs/007904975/functions/connect.html
                #
                # So we have a conundrum: if EINTR means that the connect() hasn't
                # happened (like it does for essentially every other syscall),
                # then InterruptedError should be caught and retried. If EINTR
                # means that the connect() has successfully started, then
                # InterruptedError should be caught and ignored. Which should we
                # do?
                #
                # In practice, the resolution is probably that non-blocking
                # connect simply never returns EINTR, so the question of how to
                # handle it is moot.  Someone spelunked macOS/FreeBSD and
                # confirmed this is true there:
                #
                #   https://stackoverflow.com/questions/14134440/eintr-and-non-blocking-calls
                #
                # and exarkun seems to think it's true in general of non-blocking
                # calls:
                #
                #   https://twistedmatrix.com/pipermail/twisted-python/2010-September/022864.html
                # (and indeed, AFAICT twisted doesn't try to handle
                # InterruptedError).
                #
                # So we don't try to catch InterruptedError. This way if it
                # happens, someone will hopefully tell us, and then hopefully we
                # can investigate their system to figure out what its semantics
                # are.
                return self._sock.connect(address)
            # It raised BlockingIOError, meaning that it's started the
            # connection attempt. We wait for it to complete:
            await _core.wait_writable(self._sock)
        except trio.Cancelled:
            # We can't really cancel a connect, and the socket is in an
            # indeterminate state. Better to close it so we don't get
            # confused.
            self._sock.close()
            raise
        # Okay, the connect finished, but it might have failed:
        err = self._sock.getsockopt(_stdlib_socket.SOL_SOCKET, _stdlib_socket.SO_ERROR)
        if err != 0:
            raise OSError(err, f"Error connecting to {address!r}: {os.strerror(err)}")

    ################################################################
    # recv
    ################################################################

    # Not possible to typecheck with a Callable (due to DefaultArg), nor with a
    # callback Protocol (https://github.com/python/typing/discussions/1040)
    # but this seems to work. If not explicitly defined then pyright --verifytypes will
    # complain about AmbiguousType
    if TYPE_CHECKING:

        def recv(__self, __buflen: int, __flags: int = 0) -> Awaitable[bytes]: ...

    # _make_simple_sock_method_wrapper is typed, so this checks that the above is correct
    # this requires that we refrain from using `/` to specify pos-only
    # args, or mypy thinks the signature differs from typeshed.
    recv = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recv, _core.wait_readable
    )

    ################################################################
    # recv_into
    ################################################################

    if TYPE_CHECKING:

        def recv_into(
            __self, buffer: Buffer, nbytes: int = 0, flags: int = 0
        ) -> Awaitable[int]: ...

    recv_into = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recv_into, _core.wait_readable
    )

    ################################################################
    # recvfrom
    ################################################################

    if TYPE_CHECKING:
        # return type of socket.socket.recvfrom in typeshed is tuple[bytes, Any]
        def recvfrom(
            __self, __bufsize: int, __flags: int = 0
        ) -> Awaitable[tuple[bytes, AddressFormat]]: ...

    recvfrom = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recvfrom, _core.wait_readable
    )

    ################################################################
    # recvfrom_into
    ################################################################

    if TYPE_CHECKING:
        # return type of socket.socket.recvfrom_into in typeshed is tuple[bytes, Any]
        def recvfrom_into(
            __self, buffer: Buffer, nbytes: int = 0, flags: int = 0
        ) -> Awaitable[tuple[int, AddressFormat]]: ...

    recvfrom_into = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.recvfrom_into, _core.wait_readable
    )

    ################################################################
    # recvmsg
    ################################################################

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg")
    ):
        if TYPE_CHECKING:

            def recvmsg(
                __self, __bufsize: int, __ancbufsize: int = 0, __flags: int = 0
            ) -> Awaitable[tuple[bytes, list[tuple[int, int, bytes]], int, Any]]: ...

        recvmsg = _make_simple_sock_method_wrapper(
            _stdlib_socket.socket.recvmsg, _core.wait_readable, maybe_avail=True
        )

    ################################################################
    # recvmsg_into
    ################################################################

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "recvmsg_into")
    ):
        if TYPE_CHECKING:

            def recvmsg_into(
                __self,
                __buffers: Iterable[Buffer],
                __ancbufsize: int = 0,
                __flags: int = 0,
            ) -> Awaitable[tuple[int, list[tuple[int, int, bytes]], int, Any]]: ...

        recvmsg_into = _make_simple_sock_method_wrapper(
            _stdlib_socket.socket.recvmsg_into, _core.wait_readable, maybe_avail=True
        )

    ################################################################
    # send
    ################################################################

    if TYPE_CHECKING:

        def send(__self, __bytes: Buffer, __flags: int = 0) -> Awaitable[int]: ...

    send = _make_simple_sock_method_wrapper(
        _stdlib_socket.socket.send, _core.wait_writable
    )

    ################################################################
    # sendto
    ################################################################

    @overload
    async def sendto(
        self, __data: Buffer, __address: tuple[object, ...] | str | Buffer
    ) -> int: ...

    @overload
    async def sendto(
        self, __data: Buffer, __flags: int, __address: tuple[object, ...] | str | Buffer
    ) -> int: ...

    @_wraps(_stdlib_socket.socket.sendto, assigned=(), updated=())  # type: ignore[misc]
    async def sendto(self, *args: Any) -> int:
        """Similar to :meth:`socket.socket.sendto`, but async."""
        # args is: data[, flags], address
        # and kwargs are not accepted
        args_list = list(args)
        args_list[-1] = await self._resolve_address_nocp(args[-1], local=False)
        # args_list is Any, which isn't the signature of sendto().
        # We don't care about invalid types, sendto() will do the checking.
        return await self._nonblocking_helper(
            _core.wait_writable,
            _stdlib_socket.socket.sendto,  # type: ignore[arg-type]
            *args_list,
        )

    ################################################################
    # sendmsg
    ################################################################

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(_stdlib_socket.socket, "sendmsg")
    ):

        @_wraps(_stdlib_socket.socket.sendmsg, assigned=(), updated=())
        async def sendmsg(
            self,
            __buffers: Iterable[Buffer],
            __ancdata: Iterable[tuple[int, int, Buffer]] = (),
            __flags: int = 0,
            __address: AddressFormat | None = None,
        ) -> int:
            """Similar to :meth:`socket.socket.sendmsg`, but async.

            Only available on platforms where :meth:`socket.socket.sendmsg` is
            available.

            """
            if __address is not None:
                __address = await self._resolve_address_nocp(__address, local=False)
            return await self._nonblocking_helper(
                _core.wait_writable,
                _stdlib_socket.socket.sendmsg,
                __buffers,
                __ancdata,
                __flags,
                __address,
            )

    ################################################################
    # sendfile
    ################################################################

    # Not implemented yet:
    # async def sendfile(self, file, offset=0, count=None):
    #     XX

    # Intentionally omitted:
    #   sendall
    #   makefile
    #   setblocking/getblocking
    #   settimeout/gettimeout
    #   timeout
