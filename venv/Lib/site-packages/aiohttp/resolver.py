import asyncio
import socket
import weakref
from typing import Any, Dict, Final, List, Optional, Tuple, Type, Union

from .abc import AbstractResolver, ResolveResult

__all__ = ("ThreadedResolver", "AsyncResolver", "DefaultResolver")


try:
    import aiodns

    aiodns_default = hasattr(aiodns.DNSResolver, "getaddrinfo")
except ImportError:  # pragma: no cover
    aiodns = None  # type: ignore[assignment]
    aiodns_default = False


_NUMERIC_SOCKET_FLAGS = socket.AI_NUMERICHOST | socket.AI_NUMERICSERV
_NAME_SOCKET_FLAGS = socket.NI_NUMERICHOST | socket.NI_NUMERICSERV
_AI_ADDRCONFIG = socket.AI_ADDRCONFIG
if hasattr(socket, "AI_MASK"):
    _AI_ADDRCONFIG &= socket.AI_MASK


class ThreadedResolver(AbstractResolver):
    """Threaded resolver.

    Uses an Executor for synchronous getaddrinfo() calls.
    concurrent.futures.ThreadPoolExecutor is used by default.
    """

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._loop = loop or asyncio.get_running_loop()

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> List[ResolveResult]:
        infos = await self._loop.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
            family=family,
            flags=_AI_ADDRCONFIG,
        )

        hosts: List[ResolveResult] = []
        for family, _, proto, _, address in infos:
            if family == socket.AF_INET6:
                if len(address) < 3:
                    # IPv6 is not supported by Python build,
                    # or IPv6 is not enabled in the host
                    continue
                if address[3]:
                    # This is essential for link-local IPv6 addresses.
                    # LL IPv6 is a VERY rare case. Strictly speaking, we should use
                    # getnameinfo() unconditionally, but performance makes sense.
                    resolved_host, _port = await self._loop.getnameinfo(
                        address, _NAME_SOCKET_FLAGS
                    )
                    port = int(_port)
                else:
                    resolved_host, port = address[:2]
            else:  # IPv4
                assert family == socket.AF_INET
                resolved_host, port = address  # type: ignore[misc]
            hosts.append(
                ResolveResult(
                    hostname=host,
                    host=resolved_host,
                    port=port,
                    family=family,
                    proto=proto,
                    flags=_NUMERIC_SOCKET_FLAGS,
                )
            )

        return hosts

    async def close(self) -> None:
        pass


class AsyncResolver(AbstractResolver):
    """Use the `aiodns` package to make asynchronous DNS lookups"""

    def __init__(
        self,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if aiodns is None:
            raise RuntimeError("Resolver requires aiodns library")

        self._loop = loop or asyncio.get_running_loop()
        self._manager: Optional[_DNSResolverManager] = None
        # If custom args are provided, create a dedicated resolver instance
        # This means each AsyncResolver with custom args gets its own
        # aiodns.DNSResolver instance
        if args or kwargs:
            self._resolver = aiodns.DNSResolver(*args, **kwargs)
            return
        # Use the shared resolver from the manager for default arguments
        self._manager = _DNSResolverManager()
        self._resolver = self._manager.get_resolver(self, self._loop)

        if not hasattr(self._resolver, "gethostbyname"):
            # aiodns 1.1 is not available, fallback to DNSResolver.query
            self.resolve = self._resolve_with_query  # type: ignore

    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> List[ResolveResult]:
        try:
            resp = await self._resolver.getaddrinfo(
                host,
                port=port,
                type=socket.SOCK_STREAM,
                family=family,
                flags=_AI_ADDRCONFIG,
            )
        except aiodns.error.DNSError as exc:
            msg = exc.args[1] if len(exc.args) >= 1 else "DNS lookup failed"
            raise OSError(None, msg) from exc
        hosts: List[ResolveResult] = []
        for node in resp.nodes:
            address: Union[Tuple[bytes, int], Tuple[bytes, int, int, int]] = node.addr
            family = node.family
            if family == socket.AF_INET6:
                if len(address) > 3 and address[3]:
                    # This is essential for link-local IPv6 addresses.
                    # LL IPv6 is a VERY rare case. Strictly speaking, we should use
                    # getnameinfo() unconditionally, but performance makes sense.
                    result = await self._resolver.getnameinfo(
                        (address[0].decode("ascii"), *address[1:]),
                        _NAME_SOCKET_FLAGS,
                    )
                    resolved_host = result.node
                else:
                    resolved_host = address[0].decode("ascii")
                    port = address[1]
            else:  # IPv4
                assert family == socket.AF_INET
                resolved_host = address[0].decode("ascii")
                port = address[1]
            hosts.append(
                ResolveResult(
                    hostname=host,
                    host=resolved_host,
                    port=port,
                    family=family,
                    proto=0,
                    flags=_NUMERIC_SOCKET_FLAGS,
                )
            )

        if not hosts:
            raise OSError(None, "DNS lookup failed")

        return hosts

    async def _resolve_with_query(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> List[Dict[str, Any]]:
        qtype: Final = "AAAA" if family == socket.AF_INET6 else "A"

        try:
            resp = await self._resolver.query(host, qtype)
        except aiodns.error.DNSError as exc:
            msg = exc.args[1] if len(exc.args) >= 1 else "DNS lookup failed"
            raise OSError(None, msg) from exc

        hosts = []
        for rr in resp:
            hosts.append(
                {
                    "hostname": host,
                    "host": rr.host,
                    "port": port,
                    "family": family,
                    "proto": 0,
                    "flags": socket.AI_NUMERICHOST,
                }
            )

        if not hosts:
            raise OSError(None, "DNS lookup failed")

        return hosts

    async def close(self) -> None:
        if self._manager:
            # Release the resolver from the manager if using the shared resolver
            self._manager.release_resolver(self, self._loop)
            self._manager = None  # Clear reference to manager
            self._resolver = None  # type: ignore[assignment] # Clear reference to resolver
            return
        # Otherwise cancel our dedicated resolver
        if self._resolver is not None:
            self._resolver.cancel()
        self._resolver = None  # type: ignore[assignment] # Clear reference


class _DNSResolverManager:
    """Manager for aiodns.DNSResolver objects.

    This class manages shared aiodns.DNSResolver instances
    with no custom arguments across different event loops.
    """

    _instance: Optional["_DNSResolverManager"] = None

    def __new__(cls) -> "_DNSResolverManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        # Use WeakKeyDictionary to allow event loops to be garbage collected
        self._loop_data: weakref.WeakKeyDictionary[
            asyncio.AbstractEventLoop,
            tuple["aiodns.DNSResolver", weakref.WeakSet["AsyncResolver"]],
        ] = weakref.WeakKeyDictionary()

    def get_resolver(
        self, client: "AsyncResolver", loop: asyncio.AbstractEventLoop
    ) -> "aiodns.DNSResolver":
        """Get or create the shared aiodns.DNSResolver instance for a specific event loop.

        Args:
            client: The AsyncResolver instance requesting the resolver.
                   This is required to track resolver usage.
            loop: The event loop to use for the resolver.
        """
        # Create a new resolver and client set for this loop if it doesn't exist
        if loop not in self._loop_data:
            resolver = aiodns.DNSResolver(loop=loop)
            client_set: weakref.WeakSet["AsyncResolver"] = weakref.WeakSet()
            self._loop_data[loop] = (resolver, client_set)
        else:
            # Get the existing resolver and client set
            resolver, client_set = self._loop_data[loop]

        # Register this client with the loop
        client_set.add(client)
        return resolver

    def release_resolver(
        self, client: "AsyncResolver", loop: asyncio.AbstractEventLoop
    ) -> None:
        """Release the resolver for an AsyncResolver client when it's closed.

        Args:
            client: The AsyncResolver instance to release.
            loop: The event loop the resolver was using.
        """
        # Remove client from its loop's tracking
        current_loop_data = self._loop_data.get(loop)
        if current_loop_data is None:
            return
        resolver, client_set = current_loop_data
        client_set.discard(client)
        # If no more clients for this loop, cancel and remove its resolver
        if not client_set:
            if resolver is not None:
                resolver.cancel()
            del self._loop_data[loop]


_DefaultType = Type[Union[AsyncResolver, ThreadedResolver]]
DefaultResolver: _DefaultType = AsyncResolver if aiodns_default else ThreadedResolver
