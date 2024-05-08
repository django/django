import asyncio
import copy
import enum
import inspect
import socket
import ssl
import sys
import warnings
import weakref
from abc import abstractmethod
from itertools import chain
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import ParseResult, parse_qs, unquote, urlparse

# the functionality is available in 3.11.x but has a major issue before
# 3.11.3. See https://github.com/redis/redis-py/issues/2633
if sys.version_info >= (3, 11, 3):
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout

from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.compat import Protocol, TypedDict
from redis.connection import DEFAULT_RESP_VERSION
from redis.credentials import CredentialProvider, UsernamePasswordCredentialProvider
from redis.exceptions import (
    AuthenticationError,
    AuthenticationWrongNumberOfArgsError,
    ConnectionError,
    DataError,
    RedisError,
    ResponseError,
    TimeoutError,
)
from redis.typing import EncodableT
from redis.utils import HIREDIS_AVAILABLE, get_lib_version, str_if_bytes

from .._parsers import (
    BaseParser,
    Encoder,
    _AsyncHiredisParser,
    _AsyncRESP2Parser,
    _AsyncRESP3Parser,
)

SYM_STAR = b"*"
SYM_DOLLAR = b"$"
SYM_CRLF = b"\r\n"
SYM_LF = b"\n"
SYM_EMPTY = b""


class _Sentinel(enum.Enum):
    sentinel = object()


SENTINEL = _Sentinel.sentinel


DefaultParser: Type[Union[_AsyncRESP2Parser, _AsyncRESP3Parser, _AsyncHiredisParser]]
if HIREDIS_AVAILABLE:
    DefaultParser = _AsyncHiredisParser
else:
    DefaultParser = _AsyncRESP2Parser


class ConnectCallbackProtocol(Protocol):
    def __call__(self, connection: "AbstractConnection"):
        ...


class AsyncConnectCallbackProtocol(Protocol):
    async def __call__(self, connection: "AbstractConnection"):
        ...


ConnectCallbackT = Union[ConnectCallbackProtocol, AsyncConnectCallbackProtocol]


class AbstractConnection:
    """Manages communication to and from a Redis server"""

    __slots__ = (
        "db",
        "username",
        "client_name",
        "lib_name",
        "lib_version",
        "credential_provider",
        "password",
        "socket_timeout",
        "socket_connect_timeout",
        "redis_connect_func",
        "retry_on_timeout",
        "retry_on_error",
        "health_check_interval",
        "next_health_check",
        "last_active_at",
        "encoder",
        "ssl_context",
        "protocol",
        "_reader",
        "_writer",
        "_parser",
        "_connect_callbacks",
        "_buffer_cutoff",
        "_lock",
        "_socket_read_size",
        "__dict__",
    )

    def __init__(
        self,
        *,
        db: Union[str, int] = 0,
        password: Optional[str] = None,
        socket_timeout: Optional[float] = None,
        socket_connect_timeout: Optional[float] = None,
        retry_on_timeout: bool = False,
        retry_on_error: Union[list, _Sentinel] = SENTINEL,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        decode_responses: bool = False,
        parser_class: Type[BaseParser] = DefaultParser,
        socket_read_size: int = 65536,
        health_check_interval: float = 0,
        client_name: Optional[str] = None,
        lib_name: Optional[str] = "redis-py",
        lib_version: Optional[str] = get_lib_version(),
        username: Optional[str] = None,
        retry: Optional[Retry] = None,
        redis_connect_func: Optional[ConnectCallbackT] = None,
        encoder_class: Type[Encoder] = Encoder,
        credential_provider: Optional[CredentialProvider] = None,
        protocol: Optional[int] = 2,
    ):
        if (username or password) and credential_provider is not None:
            raise DataError(
                "'username' and 'password' cannot be passed along with 'credential_"
                "provider'. Please provide only one of the following arguments: \n"
                "1. 'password' and (optional) 'username'\n"
                "2. 'credential_provider'"
            )
        self.db = db
        self.client_name = client_name
        self.lib_name = lib_name
        self.lib_version = lib_version
        self.credential_provider = credential_provider
        self.password = password
        self.username = username
        self.socket_timeout = socket_timeout
        if socket_connect_timeout is None:
            socket_connect_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        if retry_on_error is SENTINEL:
            retry_on_error = []
        if retry_on_timeout:
            retry_on_error.append(TimeoutError)
            retry_on_error.append(socket.timeout)
            retry_on_error.append(asyncio.TimeoutError)
        self.retry_on_error = retry_on_error
        if retry or retry_on_error:
            if not retry:
                self.retry = Retry(NoBackoff(), 1)
            else:
                # deep-copy the Retry object as it is mutable
                self.retry = copy.deepcopy(retry)
            # Update the retry's supported errors with the specified errors
            self.retry.update_supported_errors(retry_on_error)
        else:
            self.retry = Retry(NoBackoff(), 0)
        self.health_check_interval = health_check_interval
        self.next_health_check: float = -1
        self.encoder = encoder_class(encoding, encoding_errors, decode_responses)
        self.redis_connect_func = redis_connect_func
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._socket_read_size = socket_read_size
        self.set_parser(parser_class)
        self._connect_callbacks: List[weakref.WeakMethod[ConnectCallbackT]] = []
        self._buffer_cutoff = 6000
        try:
            p = int(protocol)
        except TypeError:
            p = DEFAULT_RESP_VERSION
        except ValueError:
            raise ConnectionError("protocol must be an integer")
        finally:
            if p < 2 or p > 3:
                raise ConnectionError("protocol must be either 2 or 3")
            self.protocol = protocol

    def __del__(self, _warnings: Any = warnings):
        # For some reason, the individual streams don't get properly garbage
        # collected and therefore produce no resource warnings.  We add one
        # here, in the same style as those from the stdlib.
        if getattr(self, "_writer", None):
            _warnings.warn(
                f"unclosed Connection {self!r}", ResourceWarning, source=self
            )
            self._close()

    def _close(self):
        """
        Internal method to silently close the connection without waiting
        """
        if self._writer:
            self._writer.close()
            self._writer = self._reader = None

    def __repr__(self):
        repr_args = ",".join((f"{k}={v}" for k, v in self.repr_pieces()))
        return f"{self.__class__.__name__}<{repr_args}>"

    @abstractmethod
    def repr_pieces(self):
        pass

    @property
    def is_connected(self):
        return self._reader is not None and self._writer is not None

    def register_connect_callback(self, callback):
        """
        Register a callback to be called when the connection is established either
        initially or reconnected.  This allows listeners to issue commands that
        are ephemeral to the connection, for example pub/sub subscription or
        key tracking.  The callback must be a _method_ and will be kept as
        a weak reference.
        """
        wm = weakref.WeakMethod(callback)
        if wm not in self._connect_callbacks:
            self._connect_callbacks.append(wm)

    def deregister_connect_callback(self, callback):
        """
        De-register a previously registered callback.  It will no-longer receive
        notifications on connection events.  Calling this is not required when the
        listener goes away, since the callbacks are kept as weak methods.
        """
        try:
            self._connect_callbacks.remove(weakref.WeakMethod(callback))
        except ValueError:
            pass

    def set_parser(self, parser_class: Type[BaseParser]) -> None:
        """
        Creates a new instance of parser_class with socket size:
        _socket_read_size and assigns it to the parser for the connection
        :param parser_class: The required parser class
        """
        self._parser = parser_class(socket_read_size=self._socket_read_size)

    async def connect(self):
        """Connects to the Redis server if not already connected"""
        if self.is_connected:
            return
        try:
            await self.retry.call_with_retry(
                lambda: self._connect(), lambda error: self.disconnect()
            )
        except asyncio.CancelledError:
            raise  # in 3.7 and earlier, this is an Exception, not BaseException
        except (socket.timeout, asyncio.TimeoutError):
            raise TimeoutError("Timeout connecting to server")
        except OSError as e:
            raise ConnectionError(self._error_message(e))
        except Exception as exc:
            raise ConnectionError(exc) from exc

        try:
            if not self.redis_connect_func:
                # Use the default on_connect function
                await self.on_connect()
            else:
                # Use the passed function redis_connect_func
                await self.redis_connect_func(self) if asyncio.iscoroutinefunction(
                    self.redis_connect_func
                ) else self.redis_connect_func(self)
        except RedisError:
            # clean up after any error in on_connect
            await self.disconnect()
            raise

        # run any user callbacks. right now the only internal callback
        # is for pubsub channel/pattern resubscription
        # first, remove any dead weakrefs
        self._connect_callbacks = [ref for ref in self._connect_callbacks if ref()]
        for ref in self._connect_callbacks:
            callback = ref()
            task = callback(self)
            if task and inspect.isawaitable(task):
                await task

    @abstractmethod
    async def _connect(self):
        pass

    @abstractmethod
    def _host_error(self) -> str:
        pass

    @abstractmethod
    def _error_message(self, exception: BaseException) -> str:
        pass

    async def on_connect(self) -> None:
        """Initialize the connection, authenticate and select a database"""
        self._parser.on_connect(self)
        parser = self._parser

        auth_args = None
        # if credential provider or username and/or password are set, authenticate
        if self.credential_provider or (self.username or self.password):
            cred_provider = (
                self.credential_provider
                or UsernamePasswordCredentialProvider(self.username, self.password)
            )
            auth_args = cred_provider.get_credentials()
            # if resp version is specified and we have auth args,
            # we need to send them via HELLO
        if auth_args and self.protocol not in [2, "2"]:
            if isinstance(self._parser, _AsyncRESP2Parser):
                self.set_parser(_AsyncRESP3Parser)
                # update cluster exception classes
                self._parser.EXCEPTION_CLASSES = parser.EXCEPTION_CLASSES
                self._parser.on_connect(self)
            if len(auth_args) == 1:
                auth_args = ["default", auth_args[0]]
            await self.send_command("HELLO", self.protocol, "AUTH", *auth_args)
            response = await self.read_response()
            if response.get(b"proto") != int(self.protocol) and response.get(
                "proto"
            ) != int(self.protocol):
                raise ConnectionError("Invalid RESP version")
        # avoid checking health here -- PING will fail if we try
        # to check the health prior to the AUTH
        elif auth_args:
            await self.send_command("AUTH", *auth_args, check_health=False)

            try:
                auth_response = await self.read_response()
            except AuthenticationWrongNumberOfArgsError:
                # a username and password were specified but the Redis
                # server seems to be < 6.0.0 which expects a single password
                # arg. retry auth with just the password.
                # https://github.com/andymccurdy/redis-py/issues/1274
                await self.send_command("AUTH", auth_args[-1], check_health=False)
                auth_response = await self.read_response()

            if str_if_bytes(auth_response) != "OK":
                raise AuthenticationError("Invalid Username or Password")

        # if resp version is specified, switch to it
        elif self.protocol not in [2, "2"]:
            if isinstance(self._parser, _AsyncRESP2Parser):
                self.set_parser(_AsyncRESP3Parser)
                # update cluster exception classes
                self._parser.EXCEPTION_CLASSES = parser.EXCEPTION_CLASSES
                self._parser.on_connect(self)
            await self.send_command("HELLO", self.protocol)
            response = await self.read_response()
            # if response.get(b"proto") != self.protocol and response.get(
            #     "proto"
            # ) != self.protocol:
            #     raise ConnectionError("Invalid RESP version")

        # if a client_name is given, set it
        if self.client_name:
            await self.send_command("CLIENT", "SETNAME", self.client_name)
            if str_if_bytes(await self.read_response()) != "OK":
                raise ConnectionError("Error setting client name")

        # set the library name and version, pipeline for lower startup latency
        if self.lib_name:
            await self.send_command("CLIENT", "SETINFO", "LIB-NAME", self.lib_name)
        if self.lib_version:
            await self.send_command("CLIENT", "SETINFO", "LIB-VER", self.lib_version)
        # if a database is specified, switch to it. Also pipeline this
        if self.db:
            await self.send_command("SELECT", self.db)

        # read responses from pipeline
        for _ in (sent for sent in (self.lib_name, self.lib_version) if sent):
            try:
                await self.read_response()
            except ResponseError:
                pass

        if self.db:
            if str_if_bytes(await self.read_response()) != "OK":
                raise ConnectionError("Invalid Database")

    async def disconnect(self, nowait: bool = False) -> None:
        """Disconnects from the Redis server"""
        try:
            async with async_timeout(self.socket_connect_timeout):
                self._parser.on_disconnect()
                if not self.is_connected:
                    return
                try:
                    self._writer.close()  # type: ignore[union-attr]
                    # wait for close to finish, except when handling errors and
                    # forcefully disconnecting.
                    if not nowait:
                        await self._writer.wait_closed()  # type: ignore[union-attr]
                except OSError:
                    pass
                finally:
                    self._reader = None
                    self._writer = None
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Timed out closing connection after {self.socket_connect_timeout}"
            ) from None

    async def _send_ping(self):
        """Send PING, expect PONG in return"""
        await self.send_command("PING", check_health=False)
        if str_if_bytes(await self.read_response()) != "PONG":
            raise ConnectionError("Bad response from PING health check")

    async def _ping_failed(self, error):
        """Function to call when PING fails"""
        await self.disconnect()

    async def check_health(self):
        """Check the health of the connection with a PING/PONG"""
        if (
            self.health_check_interval
            and asyncio.get_running_loop().time() > self.next_health_check
        ):
            await self.retry.call_with_retry(self._send_ping, self._ping_failed)

    async def _send_packed_command(self, command: Iterable[bytes]) -> None:
        self._writer.writelines(command)
        await self._writer.drain()

    async def send_packed_command(
        self, command: Union[bytes, str, Iterable[bytes]], check_health: bool = True
    ) -> None:
        if not self.is_connected:
            await self.connect()
        elif check_health:
            await self.check_health()

        try:
            if isinstance(command, str):
                command = command.encode()
            if isinstance(command, bytes):
                command = [command]
            if self.socket_timeout:
                await asyncio.wait_for(
                    self._send_packed_command(command), self.socket_timeout
                )
            else:
                self._writer.writelines(command)
                await self._writer.drain()
        except asyncio.TimeoutError:
            await self.disconnect(nowait=True)
            raise TimeoutError("Timeout writing to socket") from None
        except OSError as e:
            await self.disconnect(nowait=True)
            if len(e.args) == 1:
                err_no, errmsg = "UNKNOWN", e.args[0]
            else:
                err_no = e.args[0]
                errmsg = e.args[1]
            raise ConnectionError(
                f"Error {err_no} while writing to socket. {errmsg}."
            ) from e
        except BaseException:
            # BaseExceptions can be raised when a socket send operation is not
            # finished, e.g. due to a timeout.  Ideally, a caller could then re-try
            # to send un-sent data. However, the send_packed_command() API
            # does not support it so there is no point in keeping the connection open.
            await self.disconnect(nowait=True)
            raise

    async def send_command(self, *args: Any, **kwargs: Any) -> None:
        """Pack and send a command to the Redis server"""
        await self.send_packed_command(
            self.pack_command(*args), check_health=kwargs.get("check_health", True)
        )

    async def can_read_destructive(self):
        """Poll the socket to see if there's data that can be read."""
        try:
            return await self._parser.can_read_destructive()
        except OSError as e:
            await self.disconnect(nowait=True)
            host_error = self._host_error()
            raise ConnectionError(f"Error while reading from {host_error}: {e.args}")

    async def read_response(
        self,
        disable_decoding: bool = False,
        timeout: Optional[float] = None,
        *,
        disconnect_on_error: bool = True,
        push_request: Optional[bool] = False,
    ):
        """Read the response from a previously sent command"""
        read_timeout = timeout if timeout is not None else self.socket_timeout
        host_error = self._host_error()
        try:
            if (
                read_timeout is not None
                and self.protocol in ["3", 3]
                and not HIREDIS_AVAILABLE
            ):
                async with async_timeout(read_timeout):
                    response = await self._parser.read_response(
                        disable_decoding=disable_decoding, push_request=push_request
                    )
            elif read_timeout is not None:
                async with async_timeout(read_timeout):
                    response = await self._parser.read_response(
                        disable_decoding=disable_decoding
                    )
            elif self.protocol in ["3", 3] and not HIREDIS_AVAILABLE:
                response = await self._parser.read_response(
                    disable_decoding=disable_decoding, push_request=push_request
                )
            else:
                response = await self._parser.read_response(
                    disable_decoding=disable_decoding
                )
        except asyncio.TimeoutError:
            if timeout is not None:
                # user requested timeout, return None. Operation can be retried
                return None
            # it was a self.socket_timeout error.
            if disconnect_on_error:
                await self.disconnect(nowait=True)
            raise TimeoutError(f"Timeout reading from {host_error}")
        except OSError as e:
            if disconnect_on_error:
                await self.disconnect(nowait=True)
            raise ConnectionError(f"Error while reading from {host_error} : {e.args}")
        except BaseException:
            # Also by default close in case of BaseException.  A lot of code
            # relies on this behaviour when doing Command/Response pairs.
            # See #1128.
            if disconnect_on_error:
                await self.disconnect(nowait=True)
            raise

        if self.health_check_interval:
            next_time = asyncio.get_running_loop().time() + self.health_check_interval
            self.next_health_check = next_time

        if isinstance(response, ResponseError):
            raise response from None
        return response

    def pack_command(self, *args: EncodableT) -> List[bytes]:
        """Pack a series of arguments into the Redis protocol"""
        output = []
        # the client might have included 1 or more literal arguments in
        # the command name, e.g., 'CONFIG GET'. The Redis server expects these
        # arguments to be sent separately, so split the first argument
        # manually. These arguments should be bytestrings so that they are
        # not encoded.
        assert not isinstance(args[0], float)
        if isinstance(args[0], str):
            args = tuple(args[0].encode().split()) + args[1:]
        elif b" " in args[0]:
            args = tuple(args[0].split()) + args[1:]

        buff = SYM_EMPTY.join((SYM_STAR, str(len(args)).encode(), SYM_CRLF))

        buffer_cutoff = self._buffer_cutoff
        for arg in map(self.encoder.encode, args):
            # to avoid large string mallocs, chunk the command into the
            # output list if we're sending large values or memoryviews
            arg_length = len(arg)
            if (
                len(buff) > buffer_cutoff
                or arg_length > buffer_cutoff
                or isinstance(arg, memoryview)
            ):
                buff = SYM_EMPTY.join(
                    (buff, SYM_DOLLAR, str(arg_length).encode(), SYM_CRLF)
                )
                output.append(buff)
                output.append(arg)
                buff = SYM_CRLF
            else:
                buff = SYM_EMPTY.join(
                    (
                        buff,
                        SYM_DOLLAR,
                        str(arg_length).encode(),
                        SYM_CRLF,
                        arg,
                        SYM_CRLF,
                    )
                )
        output.append(buff)
        return output

    def pack_commands(self, commands: Iterable[Iterable[EncodableT]]) -> List[bytes]:
        """Pack multiple commands into the Redis protocol"""
        output: List[bytes] = []
        pieces: List[bytes] = []
        buffer_length = 0
        buffer_cutoff = self._buffer_cutoff

        for cmd in commands:
            for chunk in self.pack_command(*cmd):
                chunklen = len(chunk)
                if (
                    buffer_length > buffer_cutoff
                    or chunklen > buffer_cutoff
                    or isinstance(chunk, memoryview)
                ):
                    if pieces:
                        output.append(SYM_EMPTY.join(pieces))
                    buffer_length = 0
                    pieces = []

                if chunklen > buffer_cutoff or isinstance(chunk, memoryview):
                    output.append(chunk)
                else:
                    pieces.append(chunk)
                    buffer_length += chunklen

        if pieces:
            output.append(SYM_EMPTY.join(pieces))
        return output


class Connection(AbstractConnection):
    "Manages TCP communication to and from a Redis server"

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: Union[str, int] = 6379,
        socket_keepalive: bool = False,
        socket_keepalive_options: Optional[Mapping[int, Union[int, bytes]]] = None,
        socket_type: int = 0,
        **kwargs,
    ):
        self.host = host
        self.port = int(port)
        self.socket_keepalive = socket_keepalive
        self.socket_keepalive_options = socket_keepalive_options or {}
        self.socket_type = socket_type
        super().__init__(**kwargs)

    def repr_pieces(self):
        pieces = [("host", self.host), ("port", self.port), ("db", self.db)]
        if self.client_name:
            pieces.append(("client_name", self.client_name))
        return pieces

    def _connection_arguments(self) -> Mapping:
        return {"host": self.host, "port": self.port}

    async def _connect(self):
        """Create a TCP socket connection"""
        async with async_timeout(self.socket_connect_timeout):
            reader, writer = await asyncio.open_connection(
                **self._connection_arguments()
            )
        self._reader = reader
        self._writer = writer
        sock = writer.transport.get_extra_info("socket")
        if sock:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            try:
                # TCP_KEEPALIVE
                if self.socket_keepalive:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for k, v in self.socket_keepalive_options.items():
                        sock.setsockopt(socket.SOL_TCP, k, v)

            except (OSError, TypeError):
                # `socket_keepalive_options` might contain invalid options
                # causing an error. Do not leave the connection open.
                writer.close()
                raise

    def _host_error(self) -> str:
        return f"{self.host}:{self.port}"

    def _error_message(self, exception: BaseException) -> str:
        # args for socket.error can either be (errno, "message")
        # or just "message"

        host_error = self._host_error()

        if not exception.args:
            # asyncio has a bug where on Connection reset by peer, the
            # exception is not instanciated, so args is empty. This is the
            # workaround.
            # See: https://github.com/redis/redis-py/issues/2237
            # See: https://github.com/python/cpython/issues/94061
            return f"Error connecting to {host_error}. Connection reset by peer"
        elif len(exception.args) == 1:
            return f"Error connecting to {host_error}. {exception.args[0]}."
        else:
            return (
                f"Error {exception.args[0]} connecting to {host_error}. "
                f"{exception.args[0]}."
            )


class SSLConnection(Connection):
    """Manages SSL connections to and from the Redis server(s).
    This class extends the Connection class, adding SSL functionality, and making
    use of ssl.SSLContext (https://docs.python.org/3/library/ssl.html#ssl.SSLContext)
    """

    def __init__(
        self,
        ssl_keyfile: Optional[str] = None,
        ssl_certfile: Optional[str] = None,
        ssl_cert_reqs: str = "required",
        ssl_ca_certs: Optional[str] = None,
        ssl_ca_data: Optional[str] = None,
        ssl_check_hostname: bool = False,
        ssl_min_version: Optional[ssl.TLSVersion] = None,
        ssl_ciphers: Optional[str] = None,
        **kwargs,
    ):
        self.ssl_context: RedisSSLContext = RedisSSLContext(
            keyfile=ssl_keyfile,
            certfile=ssl_certfile,
            cert_reqs=ssl_cert_reqs,
            ca_certs=ssl_ca_certs,
            ca_data=ssl_ca_data,
            check_hostname=ssl_check_hostname,
            min_version=ssl_min_version,
            ciphers=ssl_ciphers,
        )
        super().__init__(**kwargs)

    def _connection_arguments(self) -> Mapping:
        kwargs = super()._connection_arguments()
        kwargs["ssl"] = self.ssl_context.get()
        return kwargs

    @property
    def keyfile(self):
        return self.ssl_context.keyfile

    @property
    def certfile(self):
        return self.ssl_context.certfile

    @property
    def cert_reqs(self):
        return self.ssl_context.cert_reqs

    @property
    def ca_certs(self):
        return self.ssl_context.ca_certs

    @property
    def ca_data(self):
        return self.ssl_context.ca_data

    @property
    def check_hostname(self):
        return self.ssl_context.check_hostname

    @property
    def min_version(self):
        return self.ssl_context.min_version


class RedisSSLContext:
    __slots__ = (
        "keyfile",
        "certfile",
        "cert_reqs",
        "ca_certs",
        "ca_data",
        "context",
        "check_hostname",
        "min_version",
        "ciphers",
    )

    def __init__(
        self,
        keyfile: Optional[str] = None,
        certfile: Optional[str] = None,
        cert_reqs: Optional[str] = None,
        ca_certs: Optional[str] = None,
        ca_data: Optional[str] = None,
        check_hostname: bool = False,
        min_version: Optional[ssl.TLSVersion] = None,
        ciphers: Optional[str] = None,
    ):
        self.keyfile = keyfile
        self.certfile = certfile
        if cert_reqs is None:
            self.cert_reqs = ssl.CERT_NONE
        elif isinstance(cert_reqs, str):
            CERT_REQS = {
                "none": ssl.CERT_NONE,
                "optional": ssl.CERT_OPTIONAL,
                "required": ssl.CERT_REQUIRED,
            }
            if cert_reqs not in CERT_REQS:
                raise RedisError(
                    f"Invalid SSL Certificate Requirements Flag: {cert_reqs}"
                )
            self.cert_reqs = CERT_REQS[cert_reqs]
        self.ca_certs = ca_certs
        self.ca_data = ca_data
        self.check_hostname = check_hostname
        self.min_version = min_version
        self.ciphers = ciphers
        self.context: Optional[ssl.SSLContext] = None

    def get(self) -> ssl.SSLContext:
        if not self.context:
            context = ssl.create_default_context()
            context.check_hostname = self.check_hostname
            context.verify_mode = self.cert_reqs
            if self.certfile and self.keyfile:
                context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
            if self.ca_certs or self.ca_data:
                context.load_verify_locations(cafile=self.ca_certs, cadata=self.ca_data)
            if self.min_version is not None:
                context.minimum_version = self.min_version
            if self.ciphers is not None:
                context.set_ciphers(self.ciphers)
            self.context = context
        return self.context


class UnixDomainSocketConnection(AbstractConnection):
    "Manages UDS communication to and from a Redis server"

    def __init__(self, *, path: str = "", **kwargs):
        self.path = path
        super().__init__(**kwargs)

    def repr_pieces(self) -> Iterable[Tuple[str, Union[str, int]]]:
        pieces = [("path", self.path), ("db", self.db)]
        if self.client_name:
            pieces.append(("client_name", self.client_name))
        return pieces

    async def _connect(self):
        async with async_timeout(self.socket_connect_timeout):
            reader, writer = await asyncio.open_unix_connection(path=self.path)
        self._reader = reader
        self._writer = writer
        await self.on_connect()

    def _host_error(self) -> str:
        return self.path

    def _error_message(self, exception: BaseException) -> str:
        # args for socket.error can either be (errno, "message")
        # or just "message"
        host_error = self._host_error()
        if len(exception.args) == 1:
            return (
                f"Error connecting to unix socket: {host_error}. {exception.args[0]}."
            )
        else:
            return (
                f"Error {exception.args[0]} connecting to unix socket: "
                f"{host_error}. {exception.args[1]}."
            )


FALSE_STRINGS = ("0", "F", "FALSE", "N", "NO")


def to_bool(value) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.upper() in FALSE_STRINGS:
        return False
    return bool(value)


URL_QUERY_ARGUMENT_PARSERS: Mapping[str, Callable[..., object]] = MappingProxyType(
    {
        "db": int,
        "socket_timeout": float,
        "socket_connect_timeout": float,
        "socket_keepalive": to_bool,
        "retry_on_timeout": to_bool,
        "max_connections": int,
        "health_check_interval": int,
        "ssl_check_hostname": to_bool,
        "timeout": float,
    }
)


class ConnectKwargs(TypedDict, total=False):
    username: str
    password: str
    connection_class: Type[AbstractConnection]
    host: str
    port: int
    db: int
    path: str


def parse_url(url: str) -> ConnectKwargs:
    parsed: ParseResult = urlparse(url)
    kwargs: ConnectKwargs = {}

    for name, value_list in parse_qs(parsed.query).items():
        if value_list and len(value_list) > 0:
            value = unquote(value_list[0])
            parser = URL_QUERY_ARGUMENT_PARSERS.get(name)
            if parser:
                try:
                    kwargs[name] = parser(value)
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid value for `{name}` in connection URL.")
            else:
                kwargs[name] = value

    if parsed.username:
        kwargs["username"] = unquote(parsed.username)
    if parsed.password:
        kwargs["password"] = unquote(parsed.password)

    # We only support redis://, rediss:// and unix:// schemes.
    if parsed.scheme == "unix":
        if parsed.path:
            kwargs["path"] = unquote(parsed.path)
        kwargs["connection_class"] = UnixDomainSocketConnection

    elif parsed.scheme in ("redis", "rediss"):
        if parsed.hostname:
            kwargs["host"] = unquote(parsed.hostname)
        if parsed.port:
            kwargs["port"] = int(parsed.port)

        # If there's a path argument, use it as the db argument if a
        # querystring value wasn't specified
        if parsed.path and "db" not in kwargs:
            try:
                kwargs["db"] = int(unquote(parsed.path).replace("/", ""))
            except (AttributeError, ValueError):
                pass

        if parsed.scheme == "rediss":
            kwargs["connection_class"] = SSLConnection
    else:
        valid_schemes = "redis://, rediss://, unix://"
        raise ValueError(
            f"Redis URL must specify one of the following schemes ({valid_schemes})"
        )

    return kwargs


_CP = TypeVar("_CP", bound="ConnectionPool")


class ConnectionPool:
    """
    Create a connection pool. ``If max_connections`` is set, then this
    object raises :py:class:`~redis.ConnectionError` when the pool's
    limit is reached.

    By default, TCP connections are created unless ``connection_class``
    is specified. Use :py:class:`~redis.UnixDomainSocketConnection` for
    unix sockets.

    Any additional keyword arguments are passed to the constructor of
    ``connection_class``.
    """

    @classmethod
    def from_url(cls: Type[_CP], url: str, **kwargs) -> _CP:
        """
        Return a connection pool configured from the given URL.

        For example::

            redis://[[username]:[password]]@localhost:6379/0
            rediss://[[username]:[password]]@localhost:6379/0
            unix://[username@]/path/to/socket.sock?db=0[&password=password]

        Three URL schemes are supported:

        - `redis://` creates a TCP socket connection. See more at:
          <https://www.iana.org/assignments/uri-schemes/prov/redis>
        - `rediss://` creates a SSL wrapped TCP socket connection. See more at:
          <https://www.iana.org/assignments/uri-schemes/prov/rediss>
        - ``unix://``: creates a Unix Domain Socket connection.

        The username, password, hostname, path and all querystring values
        are passed through urllib.parse.unquote in order to replace any
        percent-encoded values with their corresponding characters.

        There are several ways to specify a database number. The first value
        found will be used:

        1. A ``db`` querystring option, e.g. redis://localhost?db=0

        2. If using the redis:// or rediss:// schemes, the path argument
               of the url, e.g. redis://localhost/0

        3. A ``db`` keyword argument to this function.

        If none of these options are specified, the default db=0 is used.

        All querystring options are cast to their appropriate Python types.
        Boolean arguments can be specified with string values "True"/"False"
        or "Yes"/"No". Values that cannot be properly cast cause a
        ``ValueError`` to be raised. Once parsed, the querystring arguments
        and keyword arguments are passed to the ``ConnectionPool``'s
        class initializer. In the case of conflicting arguments, querystring
        arguments always win.
        """
        url_options = parse_url(url)
        kwargs.update(url_options)
        return cls(**kwargs)

    def __init__(
        self,
        connection_class: Type[AbstractConnection] = Connection,
        max_connections: Optional[int] = None,
        **connection_kwargs,
    ):
        max_connections = max_connections or 2**31
        if not isinstance(max_connections, int) or max_connections < 0:
            raise ValueError('"max_connections" must be a positive integer')

        self.connection_class = connection_class
        self.connection_kwargs = connection_kwargs
        self.max_connections = max_connections

        self._available_connections: List[AbstractConnection] = []
        self._in_use_connections: Set[AbstractConnection] = set()
        self.encoder_class = self.connection_kwargs.get("encoder_class", Encoder)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}"
            f"<{self.connection_class(**self.connection_kwargs)!r}>"
        )

    def reset(self):
        self._available_connections = []
        self._in_use_connections = weakref.WeakSet()

    def can_get_connection(self) -> bool:
        """Return True if a connection can be retrieved from the pool."""
        return (
            self._available_connections
            or len(self._in_use_connections) < self.max_connections
        )

    async def get_connection(self, command_name, *keys, **options):
        """Get a connected connection from the pool"""
        connection = self.get_available_connection()
        try:
            await self.ensure_connection(connection)
        except BaseException:
            await self.release(connection)
            raise

        return connection

    def get_available_connection(self):
        """Get a connection from the pool, without making sure it is connected"""
        try:
            connection = self._available_connections.pop()
        except IndexError:
            if len(self._in_use_connections) >= self.max_connections:
                raise ConnectionError("Too many connections") from None
            connection = self.make_connection()
        self._in_use_connections.add(connection)
        return connection

    def get_encoder(self):
        """Return an encoder based on encoding settings"""
        kwargs = self.connection_kwargs
        return self.encoder_class(
            encoding=kwargs.get("encoding", "utf-8"),
            encoding_errors=kwargs.get("encoding_errors", "strict"),
            decode_responses=kwargs.get("decode_responses", False),
        )

    def make_connection(self):
        """Create a new connection.  Can be overridden by child classes."""
        return self.connection_class(**self.connection_kwargs)

    async def ensure_connection(self, connection: AbstractConnection):
        """Ensure that the connection object is connected and valid"""
        await connection.connect()
        # connections that the pool provides should be ready to send
        # a command. if not, the connection was either returned to the
        # pool before all data has been read or the socket has been
        # closed. either way, reconnect and verify everything is good.
        try:
            if await connection.can_read_destructive():
                raise ConnectionError("Connection has data") from None
        except (ConnectionError, OSError):
            await connection.disconnect()
            await connection.connect()
            if await connection.can_read_destructive():
                raise ConnectionError("Connection not ready") from None

    async def release(self, connection: AbstractConnection):
        """Releases the connection back to the pool"""
        # Connections should always be returned to the correct pool,
        # not doing so is an error that will cause an exception here.
        self._in_use_connections.remove(connection)
        self._available_connections.append(connection)

    async def disconnect(self, inuse_connections: bool = True):
        """
        Disconnects connections in the pool

        If ``inuse_connections`` is True, disconnect connections that are
        current in use, potentially by other tasks. Otherwise only disconnect
        connections that are idle in the pool.
        """
        if inuse_connections:
            connections: Iterable[AbstractConnection] = chain(
                self._available_connections, self._in_use_connections
            )
        else:
            connections = self._available_connections
        resp = await asyncio.gather(
            *(connection.disconnect() for connection in connections),
            return_exceptions=True,
        )
        exc = next((r for r in resp if isinstance(r, BaseException)), None)
        if exc:
            raise exc

    async def aclose(self) -> None:
        """Close the pool, disconnecting all connections"""
        await self.disconnect()

    def set_retry(self, retry: "Retry") -> None:
        for conn in self._available_connections:
            conn.retry = retry
        for conn in self._in_use_connections:
            conn.retry = retry


class BlockingConnectionPool(ConnectionPool):
    """
    A blocking connection pool::

        >>> from redis.asyncio import Redis, BlockingConnectionPool
        >>> client = Redis.from_pool(BlockingConnectionPool())

    It performs the same function as the default
    :py:class:`~redis.asyncio.ConnectionPool` implementation, in that,
    it maintains a pool of reusable connections that can be shared by
    multiple async redis clients.

    The difference is that, in the event that a client tries to get a
    connection from the pool when all of connections are in use, rather than
    raising a :py:class:`~redis.ConnectionError` (as the default
    :py:class:`~redis.asyncio.ConnectionPool` implementation does), it
    blocks the current `Task` for a specified number of seconds until
    a connection becomes available.

    Use ``max_connections`` to increase / decrease the pool size::

        >>> pool = BlockingConnectionPool(max_connections=10)

    Use ``timeout`` to tell it either how many seconds to wait for a connection
    to become available, or to block forever:

        >>> # Block forever.
        >>> pool = BlockingConnectionPool(timeout=None)

        >>> # Raise a ``ConnectionError`` after five seconds if a connection is
        >>> # not available.
        >>> pool = BlockingConnectionPool(timeout=5)
    """

    def __init__(
        self,
        max_connections: int = 50,
        timeout: Optional[int] = 20,
        connection_class: Type[AbstractConnection] = Connection,
        queue_class: Type[asyncio.Queue] = asyncio.LifoQueue,  # deprecated
        **connection_kwargs,
    ):
        super().__init__(
            connection_class=connection_class,
            max_connections=max_connections,
            **connection_kwargs,
        )
        self._condition = asyncio.Condition()
        self.timeout = timeout

    async def get_connection(self, command_name, *keys, **options):
        """Gets a connection from the pool, blocking until one is available"""
        try:
            async with self._condition:
                async with async_timeout(self.timeout):
                    await self._condition.wait_for(self.can_get_connection)
                    connection = super().get_available_connection()
        except asyncio.TimeoutError as err:
            raise ConnectionError("No connection available.") from err

        # We now perform the connection check outside of the lock.
        try:
            await self.ensure_connection(connection)
            return connection
        except BaseException:
            await self.release(connection)
            raise

    async def release(self, connection: AbstractConnection):
        """Releases the connection back to the pool."""
        async with self._condition:
            await super().release(connection)
            self._condition.notify()
