import copy
import os
import socket
import sys
import threading
import time
import weakref
from abc import ABC, abstractmethod
from itertools import chain
from queue import Empty, Full, LifoQueue
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import parse_qs, unquote, urlparse

from redis.cache import (
    CacheEntry,
    CacheEntryStatus,
    CacheFactory,
    CacheFactoryInterface,
    CacheInterface,
    CacheKey,
    CacheProxy,
)

from ._parsers import Encoder, _HiredisParser, _RESP2Parser, _RESP3Parser
from .auth.token import TokenInterface
from .backoff import NoBackoff
from .credentials import CredentialProvider, UsernamePasswordCredentialProvider
from .driver_info import DriverInfo, resolve_driver_info
from .event import AfterConnectionReleasedEvent, EventDispatcher
from .exceptions import (
    AuthenticationError,
    AuthenticationWrongNumberOfArgsError,
    ChildDeadlockedError,
    ConnectionError,
    DataError,
    MaxConnectionsError,
    RedisError,
    ResponseError,
    TimeoutError,
)
from .maint_notifications import (
    MaintenanceState,
    MaintNotificationsConfig,
    MaintNotificationsConnectionHandler,
    MaintNotificationsPoolHandler,
    OSSMaintNotificationsHandler,
)
from .observability.attributes import (
    DB_CLIENT_CONNECTION_POOL_NAME,
    DB_CLIENT_CONNECTION_STATE,
    AttributeBuilder,
    ConnectionState,
    CSCReason,
    CSCResult,
    get_pool_name,
)
from .observability.metrics import CloseReason
from .observability.recorder import (
    init_csc_items,
    record_connection_closed,
    record_connection_create_time,
    record_connection_wait_time,
    record_csc_eviction,
    record_csc_network_saved,
    record_csc_request,
    record_error_count,
    register_csc_items_callback,
)
from .retry import Retry
from .utils import (
    CRYPTOGRAPHY_AVAILABLE,
    HIREDIS_AVAILABLE,
    SSL_AVAILABLE,
    check_protocol_version,
    compare_versions,
    deprecated_args,
    ensure_string,
    format_error_message,
    str_if_bytes,
)

if SSL_AVAILABLE:
    import ssl
    from ssl import VerifyFlags
else:
    ssl = None
    VerifyFlags = None

if HIREDIS_AVAILABLE:
    import hiredis

SYM_STAR = b"*"
SYM_DOLLAR = b"$"
SYM_CRLF = b"\r\n"
SYM_EMPTY = b""

DEFAULT_RESP_VERSION = 2

SENTINEL = object()

DefaultParser: Type[Union[_RESP2Parser, _RESP3Parser, _HiredisParser]]
if HIREDIS_AVAILABLE:
    DefaultParser = _HiredisParser
else:
    DefaultParser = _RESP2Parser


class HiredisRespSerializer:
    def pack(self, *args: List):
        """Pack a series of arguments into the Redis protocol"""
        output = []

        if isinstance(args[0], str):
            args = tuple(args[0].encode().split()) + args[1:]
        elif b" " in args[0]:
            args = tuple(args[0].split()) + args[1:]
        try:
            output.append(hiredis.pack_command(args))
        except TypeError:
            _, value, traceback = sys.exc_info()
            raise DataError(value).with_traceback(traceback)

        return output


class PythonRespSerializer:
    def __init__(self, buffer_cutoff, encode) -> None:
        self._buffer_cutoff = buffer_cutoff
        self.encode = encode

    def pack(self, *args):
        """Pack a series of arguments into the Redis protocol"""
        output = []
        # the client might have included 1 or more literal arguments in
        # the command name, e.g., 'CONFIG GET'. The Redis server expects these
        # arguments to be sent separately, so split the first argument
        # manually. These arguments should be bytestrings so that they are
        # not encoded.
        if isinstance(args[0], str):
            args = tuple(args[0].encode().split()) + args[1:]
        elif b" " in args[0]:
            args = tuple(args[0].split()) + args[1:]

        buff = SYM_EMPTY.join((SYM_STAR, str(len(args)).encode(), SYM_CRLF))

        buffer_cutoff = self._buffer_cutoff
        for arg in map(self.encode, args):
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


class ConnectionInterface:
    @abstractmethod
    def repr_pieces(self):
        pass

    @abstractmethod
    def register_connect_callback(self, callback):
        pass

    @abstractmethod
    def deregister_connect_callback(self, callback):
        pass

    @abstractmethod
    def set_parser(self, parser_class):
        pass

    @abstractmethod
    def get_protocol(self):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def on_connect(self):
        pass

    @abstractmethod
    def disconnect(self, *args, **kwargs):
        pass

    @abstractmethod
    def check_health(self):
        pass

    @abstractmethod
    def send_packed_command(self, command, check_health=True):
        pass

    @abstractmethod
    def send_command(self, *args, **kwargs):
        pass

    @abstractmethod
    def can_read(self, timeout=0):
        pass

    @abstractmethod
    def read_response(
        self,
        disable_decoding=False,
        *,
        disconnect_on_error=True,
        push_request=False,
    ):
        pass

    @abstractmethod
    def pack_command(self, *args):
        pass

    @abstractmethod
    def pack_commands(self, commands):
        pass

    @property
    @abstractmethod
    def handshake_metadata(self) -> Union[Dict[bytes, bytes], Dict[str, str]]:
        pass

    @abstractmethod
    def set_re_auth_token(self, token: TokenInterface):
        pass

    @abstractmethod
    def re_auth(self):
        pass

    @abstractmethod
    def mark_for_reconnect(self):
        """
        Mark the connection to be reconnected on the next command.
        This is useful when a connection is moved to a different node.
        """
        pass

    @abstractmethod
    def should_reconnect(self):
        """
        Returns True if the connection should be reconnected.
        """
        pass

    @abstractmethod
    def reset_should_reconnect(self):
        """
        Reset the internal flag to False.
        """
        pass


class MaintNotificationsAbstractConnection:
    """
    Abstract class for handling maintenance notifications logic.
    This class is expected to be used as base class together with ConnectionInterface.

    This class is intended to be used with multiple inheritance!

    All logic related to maintenance notifications is encapsulated in this class.
    """

    def __init__(
        self,
        maint_notifications_config: Optional[MaintNotificationsConfig],
        maint_notifications_pool_handler: Optional[
            MaintNotificationsPoolHandler
        ] = None,
        maintenance_state: "MaintenanceState" = MaintenanceState.NONE,
        maintenance_notification_hash: Optional[int] = None,
        orig_host_address: Optional[str] = None,
        orig_socket_timeout: Optional[float] = None,
        orig_socket_connect_timeout: Optional[float] = None,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
        parser: Optional[Union[_HiredisParser, _RESP3Parser]] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
    ):
        """
        Initialize the maintenance notifications for the connection.

        Args:
            maint_notifications_config (MaintNotificationsConfig): The configuration for maintenance notifications.
            maint_notifications_pool_handler (Optional[MaintNotificationsPoolHandler]): The pool handler for maintenance notifications.
            maintenance_state (MaintenanceState): The current maintenance state of the connection.
            maintenance_notification_hash (Optional[int]): The current maintenance notification hash of the connection.
            orig_host_address (Optional[str]): The original host address of the connection.
            orig_socket_timeout (Optional[float]): The original socket timeout of the connection.
            orig_socket_connect_timeout (Optional[float]): The original socket connect timeout of the connection.
            oss_cluster_maint_notifications_handler (Optional[OSSMaintNotificationsHandler]): The OSS cluster handler for maintenance notifications.
            parser (Optional[Union[_HiredisParser, _RESP3Parser]]): The parser to use for maintenance notifications.
                    If not provided, the parser from the connection is used.
                    This is useful when the parser is created after this object.
        """
        self.maint_notifications_config = maint_notifications_config
        self.maintenance_state = maintenance_state
        self.maintenance_notification_hash = maintenance_notification_hash

        if event_dispatcher is not None:
            self.event_dispatcher = event_dispatcher
        else:
            self.event_dispatcher = EventDispatcher()

        self._configure_maintenance_notifications(
            maint_notifications_pool_handler,
            orig_host_address,
            orig_socket_timeout,
            orig_socket_connect_timeout,
            oss_cluster_maint_notifications_handler,
            parser,
        )
        self._processed_start_maint_notifications = set()
        self._skipped_end_maint_notifications = set()

    @abstractmethod
    def _get_parser(self) -> Union[_HiredisParser, _RESP3Parser]:
        pass

    @abstractmethod
    def _get_socket(self) -> Optional[socket.socket]:
        pass

    @abstractmethod
    def get_protocol(self) -> Union[int, str]:
        """
        Returns:
            The RESP protocol version, or ``None`` if the protocol is not specified,
            in which case the server default will be used.
        """
        pass

    @property
    @abstractmethod
    def host(self) -> str:
        pass

    @host.setter
    @abstractmethod
    def host(self, value: str):
        pass

    @property
    @abstractmethod
    def socket_timeout(self) -> Optional[Union[float, int]]:
        pass

    @socket_timeout.setter
    @abstractmethod
    def socket_timeout(self, value: Optional[Union[float, int]]):
        pass

    @property
    @abstractmethod
    def socket_connect_timeout(self) -> Optional[Union[float, int]]:
        pass

    @socket_connect_timeout.setter
    @abstractmethod
    def socket_connect_timeout(self, value: Optional[Union[float, int]]):
        pass

    @abstractmethod
    def send_command(self, *args, **kwargs):
        pass

    @abstractmethod
    def read_response(
        self,
        disable_decoding=False,
        *,
        disconnect_on_error=True,
        push_request=False,
    ):
        pass

    @abstractmethod
    def disconnect(self, *args, **kwargs):
        pass

    def _configure_maintenance_notifications(
        self,
        maint_notifications_pool_handler: Optional[
            MaintNotificationsPoolHandler
        ] = None,
        orig_host_address=None,
        orig_socket_timeout=None,
        orig_socket_connect_timeout=None,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
        parser: Optional[Union[_HiredisParser, _RESP3Parser]] = None,
    ):
        """
        Enable maintenance notifications by setting up
        handlers and storing original connection parameters.

        Should be used ONLY with parsers that support push notifications.
        """
        if (
            not self.maint_notifications_config
            or not self.maint_notifications_config.enabled
        ):
            self._maint_notifications_pool_handler = None
            self._maint_notifications_connection_handler = None
            self._oss_cluster_maint_notifications_handler = None
            return

        if not parser:
            raise RedisError(
                "To configure maintenance notifications, a parser must be provided!"
            )

        if not isinstance(parser, _HiredisParser) and not isinstance(
            parser, _RESP3Parser
        ):
            raise RedisError(
                "Maintenance notifications are only supported with hiredis and RESP3 parsers!"
            )

        if maint_notifications_pool_handler:
            # Extract a reference to a new pool handler that copies all properties
            # of the original one and has a different connection reference
            # This is needed because when we attach the handler to the parser
            # we need to make sure that the handler has a reference to the
            # connection that the parser is attached to.
            self._maint_notifications_pool_handler = (
                maint_notifications_pool_handler.get_handler_for_connection()
            )
            self._maint_notifications_pool_handler.set_connection(self)
        else:
            self._maint_notifications_pool_handler = None

        self._maint_notifications_connection_handler = (
            MaintNotificationsConnectionHandler(self, self.maint_notifications_config)
        )

        if oss_cluster_maint_notifications_handler:
            self._oss_cluster_maint_notifications_handler = (
                oss_cluster_maint_notifications_handler
            )
        else:
            self._oss_cluster_maint_notifications_handler = None

        # Set up OSS cluster handler to parser if available
        if self._oss_cluster_maint_notifications_handler:
            parser.set_oss_cluster_maint_push_handler(
                self._oss_cluster_maint_notifications_handler.handle_notification
            )

        # Set up pool handler to parser if available
        if self._maint_notifications_pool_handler:
            parser.set_node_moving_push_handler(
                self._maint_notifications_pool_handler.handle_notification
            )

        # Set up connection handler
        parser.set_maintenance_push_handler(
            self._maint_notifications_connection_handler.handle_notification
        )

        # Store original connection parameters
        self.orig_host_address = orig_host_address if orig_host_address else self.host
        self.orig_socket_timeout = (
            orig_socket_timeout if orig_socket_timeout else self.socket_timeout
        )
        self.orig_socket_connect_timeout = (
            orig_socket_connect_timeout
            if orig_socket_connect_timeout
            else self.socket_connect_timeout
        )

    def set_maint_notifications_pool_handler_for_connection(
        self, maint_notifications_pool_handler: MaintNotificationsPoolHandler
    ):
        # Deep copy the pool handler to avoid sharing the same pool handler
        # between multiple connections, because otherwise each connection will override
        # the connection reference and the pool handler will only hold a reference
        # to the last connection that was set.
        maint_notifications_pool_handler_copy = (
            maint_notifications_pool_handler.get_handler_for_connection()
        )

        maint_notifications_pool_handler_copy.set_connection(self)
        self._get_parser().set_node_moving_push_handler(
            maint_notifications_pool_handler_copy.handle_notification
        )

        self._maint_notifications_pool_handler = maint_notifications_pool_handler_copy

        # Update maintenance notification connection handler if it doesn't exist
        if not self._maint_notifications_connection_handler:
            self._maint_notifications_connection_handler = (
                MaintNotificationsConnectionHandler(
                    self, maint_notifications_pool_handler.config
                )
            )
            self._get_parser().set_maintenance_push_handler(
                self._maint_notifications_connection_handler.handle_notification
            )
        else:
            self._maint_notifications_connection_handler.config = (
                maint_notifications_pool_handler.config
            )

    def set_maint_notifications_cluster_handler_for_connection(
        self, oss_cluster_maint_notifications_handler: OSSMaintNotificationsHandler
    ):
        self._get_parser().set_oss_cluster_maint_push_handler(
            oss_cluster_maint_notifications_handler.handle_notification
        )

        self._oss_cluster_maint_notifications_handler = (
            oss_cluster_maint_notifications_handler
        )

        # Update maintenance notification connection handler if it doesn't exist
        if not self._maint_notifications_connection_handler:
            self._maint_notifications_connection_handler = (
                MaintNotificationsConnectionHandler(
                    self, oss_cluster_maint_notifications_handler.config
                )
            )
            self._get_parser().set_maintenance_push_handler(
                self._maint_notifications_connection_handler.handle_notification
            )
        else:
            self._maint_notifications_connection_handler.config = (
                oss_cluster_maint_notifications_handler.config
            )

    def activate_maint_notifications_handling_if_enabled(self, check_health=True):
        # Send maintenance notifications handshake if RESP3 is active
        # and maintenance notifications are enabled
        # and we have a host to determine the endpoint type from
        # When the maint_notifications_config enabled mode is "auto",
        # we just log a warning if the handshake fails
        # When the mode is enabled=True, we raise an exception in case of failure
        if (
            self.get_protocol() not in [2, "2"]
            and self.maint_notifications_config
            and self.maint_notifications_config.enabled
            and self._maint_notifications_connection_handler
            and hasattr(self, "host")
        ):
            self._enable_maintenance_notifications(
                maint_notifications_config=self.maint_notifications_config,
                check_health=check_health,
            )

    def _enable_maintenance_notifications(
        self, maint_notifications_config: MaintNotificationsConfig, check_health=True
    ):
        try:
            host = getattr(self, "host", None)
            if host is None:
                raise ValueError(
                    "Cannot enable maintenance notifications for connection"
                    " object that doesn't have a host attribute."
                )
            else:
                endpoint_type = maint_notifications_config.get_endpoint_type(host, self)
                self.send_command(
                    "CLIENT",
                    "MAINT_NOTIFICATIONS",
                    "ON",
                    "moving-endpoint-type",
                    endpoint_type.value,
                    check_health=check_health,
                )
                response = self.read_response()
                if not response or str_if_bytes(response) != "OK":
                    raise ResponseError(
                        "The server doesn't support maintenance notifications"
                    )
        except Exception as e:
            if (
                isinstance(e, ResponseError)
                and maint_notifications_config.enabled == "auto"
            ):
                # Log warning but don't fail the connection
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Failed to enable maintenance notifications: {e}")
            else:
                raise

    def get_resolved_ip(self) -> Optional[str]:
        """
        Extract the resolved IP address from an
        established connection or resolve it from the host.

        First tries to get the actual IP from the socket (most accurate),
        then falls back to DNS resolution if needed.

        Args:
            connection: The connection object to extract the IP from

        Returns:
            str: The resolved IP address, or None if it cannot be determined
        """

        # Method 1: Try to get the actual IP from the established socket connection
        # This is most accurate as it shows the exact IP being used
        try:
            conn_socket = self._get_socket()
            if conn_socket is not None:
                peer_addr = conn_socket.getpeername()
                if peer_addr and len(peer_addr) >= 1:
                    # For TCP sockets, peer_addr is typically (host, port) tuple
                    # Return just the host part
                    return peer_addr[0]
        except (AttributeError, OSError):
            # Socket might not be connected or getpeername() might fail
            pass

        # Method 2: Fallback to DNS resolution of the host
        # This is less accurate but works when socket is not available
        try:
            host = getattr(self, "host", "localhost")
            port = getattr(self, "port", 6379)
            if host:
                # Use getaddrinfo to resolve the hostname to IP
                # This mimics what the connection would do during _connect()
                addr_info = socket.getaddrinfo(
                    host, port, socket.AF_UNSPEC, socket.SOCK_STREAM
                )
                if addr_info:
                    # Return the IP from the first result
                    # addr_info[0] is (family, socktype, proto, canonname, sockaddr)
                    # sockaddr[0] is the IP address
                    return str(addr_info[0][4][0])
        except (AttributeError, OSError, socket.gaierror):
            # DNS resolution might fail
            pass

        return None

    @property
    def maintenance_state(self) -> MaintenanceState:
        return self._maintenance_state

    @maintenance_state.setter
    def maintenance_state(self, state: "MaintenanceState"):
        self._maintenance_state = state

    def add_maint_start_notification(self, id: int):
        self._processed_start_maint_notifications.add(id)

    def get_processed_start_notifications(self) -> set:
        return self._processed_start_maint_notifications

    def add_skipped_end_notification(self, id: int):
        self._skipped_end_maint_notifications.add(id)

    def get_skipped_end_notifications(self) -> set:
        return self._skipped_end_maint_notifications

    def reset_received_notifications(self):
        self._processed_start_maint_notifications.clear()
        self._skipped_end_maint_notifications.clear()

    def getpeername(self):
        """
        Returns the peer name of the connection.
        """
        conn_socket = self._get_socket()
        if conn_socket:
            return conn_socket.getpeername()[0]
        return None

    def update_current_socket_timeout(self, relaxed_timeout: Optional[float] = None):
        conn_socket = self._get_socket()
        if conn_socket:
            timeout = relaxed_timeout if relaxed_timeout != -1 else self.socket_timeout
            # if the current timeout is 0 it means we are in the middle of a can_read call
            # in this case we don't want to change the timeout because the operation
            # is non-blocking and should return immediately
            # Changing the state from non-blocking to blocking in the middle of a read operation
            # will lead to a deadlock
            if conn_socket.gettimeout() != 0:
                conn_socket.settimeout(timeout)
            self.update_parser_timeout(timeout)

    def update_parser_timeout(self, timeout: Optional[float] = None):
        parser = self._get_parser()
        if parser and parser._buffer:
            if isinstance(parser, _RESP3Parser) and timeout:
                parser._buffer.socket_timeout = timeout
            elif isinstance(parser, _HiredisParser):
                parser._socket_timeout = timeout

    def set_tmp_settings(
        self,
        tmp_host_address: Optional[Union[str, object]] = SENTINEL,
        tmp_relaxed_timeout: Optional[float] = None,
    ):
        """
        The value of SENTINEL is used to indicate that the property should not be updated.
        """
        if tmp_host_address and tmp_host_address != SENTINEL:
            self.host = str(tmp_host_address)
        if tmp_relaxed_timeout != -1:
            self.socket_timeout = tmp_relaxed_timeout
            self.socket_connect_timeout = tmp_relaxed_timeout

    def reset_tmp_settings(
        self,
        reset_host_address: bool = False,
        reset_relaxed_timeout: bool = False,
    ):
        if reset_host_address:
            self.host = self.orig_host_address
        if reset_relaxed_timeout:
            self.socket_timeout = self.orig_socket_timeout
            self.socket_connect_timeout = self.orig_socket_connect_timeout


class AbstractConnection(MaintNotificationsAbstractConnection, ConnectionInterface):
    "Manages communication to and from a Redis server"

    @deprecated_args(
        args_to_warn=["lib_name", "lib_version"],
        reason="Use 'driver_info' parameter instead. "
        "lib_name and lib_version will be removed in a future version.",
    )
    def __init__(
        self,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: Optional[float] = None,
        socket_connect_timeout: Optional[float] = None,
        retry_on_timeout: bool = False,
        retry_on_error: Union[Iterable[Type[Exception]], object] = SENTINEL,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        decode_responses: bool = False,
        parser_class=DefaultParser,
        socket_read_size: int = 65536,
        health_check_interval: int = 0,
        client_name: Optional[str] = None,
        lib_name: Optional[str] = None,
        lib_version: Optional[str] = None,
        driver_info: Optional[DriverInfo] = None,
        username: Optional[str] = None,
        retry: Union[Any, None] = None,
        redis_connect_func: Optional[Callable[[], None]] = None,
        credential_provider: Optional[CredentialProvider] = None,
        protocol: Optional[int] = 2,
        command_packer: Optional[Callable[[], None]] = None,
        event_dispatcher: Optional[EventDispatcher] = None,
        maint_notifications_config: Optional[MaintNotificationsConfig] = None,
        maint_notifications_pool_handler: Optional[
            MaintNotificationsPoolHandler
        ] = None,
        maintenance_state: "MaintenanceState" = MaintenanceState.NONE,
        maintenance_notification_hash: Optional[int] = None,
        orig_host_address: Optional[str] = None,
        orig_socket_timeout: Optional[float] = None,
        orig_socket_connect_timeout: Optional[float] = None,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
    ):
        """
        Initialize a new Connection.

        To specify a retry policy for specific errors, first set
        `retry_on_error` to a list of the error/s to retry on, then set
        `retry` to a valid `Retry` object.
        To retry on TimeoutError, `retry_on_timeout` can also be set to `True`.

        Parameters
        ----------
        driver_info : DriverInfo, optional
            Driver metadata for CLIENT SETINFO. If provided, lib_name and lib_version
            are ignored. If not provided, a DriverInfo will be created from lib_name
            and lib_version (or defaults if those are also None).
        lib_name : str, optional
            **Deprecated.** Use driver_info instead. Library name for CLIENT SETINFO.
        lib_version : str, optional
            **Deprecated.** Use driver_info instead. Library version for CLIENT SETINFO.
        """
        if (username or password) and credential_provider is not None:
            raise DataError(
                "'username' and 'password' cannot be passed along with 'credential_"
                "provider'. Please provide only one of the following arguments: \n"
                "1. 'password' and (optional) 'username'\n"
                "2. 'credential_provider'"
            )
        if event_dispatcher is None:
            self._event_dispatcher = EventDispatcher()
        else:
            self._event_dispatcher = event_dispatcher
        self.pid = os.getpid()
        self.db = db
        self.client_name = client_name

        # Handle driver_info: if provided, use it; otherwise create from lib_name/lib_version
        self.driver_info = resolve_driver_info(driver_info, lib_name, lib_version)

        self.credential_provider = credential_provider
        self.password = password
        self.username = username
        self._socket_timeout = socket_timeout
        if socket_connect_timeout is None:
            socket_connect_timeout = socket_timeout
        self._socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        if retry_on_error is SENTINEL:
            retry_on_errors_list = []
        else:
            retry_on_errors_list = list(retry_on_error)
        if retry_on_timeout:
            # Add TimeoutError to the errors list to retry on
            retry_on_errors_list.append(TimeoutError)
        self.retry_on_error = retry_on_errors_list
        if retry or self.retry_on_error:
            if retry is None:
                self.retry = Retry(NoBackoff(), 1)
            else:
                # deep-copy the Retry object as it is mutable
                self.retry = copy.deepcopy(retry)
            if self.retry_on_error:
                # Update the retry's supported errors with the specified errors
                self.retry.update_supported_errors(self.retry_on_error)
        else:
            self.retry = Retry(NoBackoff(), 0)
        self.health_check_interval = health_check_interval
        self.next_health_check = 0
        self.redis_connect_func = redis_connect_func
        self.encoder = Encoder(encoding, encoding_errors, decode_responses)
        self.handshake_metadata = None
        self._sock = None
        self._socket_read_size = socket_read_size
        self._connect_callbacks = []
        self._buffer_cutoff = 6000
        self._re_auth_token: Optional[TokenInterface] = None
        try:
            p = int(protocol)
        except TypeError:
            p = DEFAULT_RESP_VERSION
        except ValueError:
            raise ConnectionError("protocol must be an integer")
        finally:
            if p < 2 or p > 3:
                raise ConnectionError("protocol must be either 2 or 3")
                # p = DEFAULT_RESP_VERSION
            self.protocol = p
        if self.protocol == 3 and parser_class == _RESP2Parser:
            # If the protocol is 3 but the parser is RESP2, change it to RESP3
            # This is needed because the parser might be set before the protocol
            # or might be provided as a kwarg to the constructor
            # We need to react on discrepancy only for RESP2 and RESP3
            # as hiredis supports both
            parser_class = _RESP3Parser
        self.set_parser(parser_class)

        self._command_packer = self._construct_command_packer(command_packer)
        self._should_reconnect = False

        # Set up maintenance notifications
        MaintNotificationsAbstractConnection.__init__(
            self,
            maint_notifications_config,
            maint_notifications_pool_handler,
            maintenance_state,
            maintenance_notification_hash,
            orig_host_address,
            orig_socket_timeout,
            orig_socket_connect_timeout,
            oss_cluster_maint_notifications_handler,
            self._parser,
            event_dispatcher=self._event_dispatcher,
        )

    def __repr__(self):
        repr_args = ",".join([f"{k}={v}" for k, v in self.repr_pieces()])
        return f"<{self.__class__.__module__}.{self.__class__.__name__}({repr_args})>"

    @abstractmethod
    def repr_pieces(self):
        pass

    def __del__(self):
        try:
            self.disconnect()
        except Exception:
            pass

    def _construct_command_packer(self, packer):
        if packer is not None:
            return packer
        elif HIREDIS_AVAILABLE:
            return HiredisRespSerializer()
        else:
            return PythonRespSerializer(self._buffer_cutoff, self.encoder.encode)

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

    def set_parser(self, parser_class):
        """
        Creates a new instance of parser_class with socket size:
        _socket_read_size and assigns it to the parser for the connection
        :param parser_class: The required parser class
        """
        self._parser = parser_class(socket_read_size=self._socket_read_size)

    def _get_parser(self) -> Union[_HiredisParser, _RESP3Parser, _RESP2Parser]:
        return self._parser

    def connect(self):
        "Connects to the Redis server if not already connected"
        # try once the socket connect with the handshake, retry the whole
        # connect/handshake flow based on retry policy
        self.retry.call_with_retry(
            lambda: self.connect_check_health(
                check_health=True, retry_socket_connect=False
            ),
            lambda error: self.disconnect(error),
        )

    def connect_check_health(
        self, check_health: bool = True, retry_socket_connect: bool = True
    ):
        if self._sock:
            return
        try:
            if retry_socket_connect:
                sock = self.retry.call_with_retry(
                    self._connect,
                    lambda error, failure_count: self.disconnect(
                        error=error, failure_count=failure_count
                    ),
                    with_failure_count=True,
                )
            else:
                sock = self._connect()
        except socket.timeout:
            e = TimeoutError("Timeout connecting to server")
            record_error_count(
                server_address=self.host,
                server_port=self.port,
                network_peer_address=self.host,
                network_peer_port=self.port,
                error_type=e,
                retry_attempts=0,
                is_internal=False,
            )
            raise e
        except OSError as e:
            e = ConnectionError(self._error_message(e))
            record_error_count(
                server_address=getattr(self, "host", None),
                server_port=getattr(self, "port", None),
                network_peer_address=getattr(self, "host", None),
                network_peer_port=getattr(self, "port", None),
                error_type=e,
                retry_attempts=0,
                is_internal=False,
            )
            raise e

        self._sock = sock
        try:
            if self.redis_connect_func is None:
                # Use the default on_connect function
                self.on_connect_check_health(check_health=check_health)
            else:
                # Use the passed function redis_connect_func
                self.redis_connect_func(self)
        except RedisError:
            # clean up after any error in on_connect
            self.disconnect()
            raise

        # run any user callbacks. right now the only internal callback
        # is for pubsub channel/pattern resubscription
        # first, remove any dead weakrefs
        self._connect_callbacks = [ref for ref in self._connect_callbacks if ref()]
        for ref in self._connect_callbacks:
            callback = ref()
            if callback:
                callback(self)

    @abstractmethod
    def _connect(self):
        pass

    @abstractmethod
    def _host_error(self):
        pass

    def _error_message(self, exception):
        return format_error_message(self._host_error(), exception)

    def on_connect(self):
        self.on_connect_check_health(check_health=True)

    def on_connect_check_health(self, check_health: bool = True):
        "Initialize the connection, authenticate and select a database"
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
            if isinstance(self._parser, _RESP2Parser):
                self.set_parser(_RESP3Parser)
                # update cluster exception classes
                self._parser.EXCEPTION_CLASSES = parser.EXCEPTION_CLASSES
                self._parser.on_connect(self)
            if len(auth_args) == 1:
                auth_args = ["default", auth_args[0]]
            # avoid checking health here -- PING will fail if we try
            # to check the health prior to the AUTH
            self.send_command(
                "HELLO", self.protocol, "AUTH", *auth_args, check_health=False
            )
            self.handshake_metadata = self.read_response()
            # if response.get(b"proto") != self.protocol and response.get(
            #     "proto"
            # ) != self.protocol:
            #     raise ConnectionError("Invalid RESP version")
        elif auth_args:
            # avoid checking health here -- PING will fail if we try
            # to check the health prior to the AUTH
            self.send_command("AUTH", *auth_args, check_health=False)

            try:
                auth_response = self.read_response()
            except AuthenticationWrongNumberOfArgsError:
                # a username and password were specified but the Redis
                # server seems to be < 6.0.0 which expects a single password
                # arg. retry auth with just the password.
                # https://github.com/andymccurdy/redis-py/issues/1274
                self.send_command("AUTH", auth_args[-1], check_health=False)
                auth_response = self.read_response()

            if str_if_bytes(auth_response) != "OK":
                raise AuthenticationError("Invalid Username or Password")

        # if resp version is specified, switch to it
        elif self.protocol not in [2, "2"]:
            if isinstance(self._parser, _RESP2Parser):
                self.set_parser(_RESP3Parser)
                # update cluster exception classes
                self._parser.EXCEPTION_CLASSES = parser.EXCEPTION_CLASSES
                self._parser.on_connect(self)
            self.send_command("HELLO", self.protocol, check_health=check_health)
            self.handshake_metadata = self.read_response()
            if (
                self.handshake_metadata.get(b"proto") != self.protocol
                and self.handshake_metadata.get("proto") != self.protocol
            ):
                raise ConnectionError("Invalid RESP version")

        # Activate maintenance notifications for this connection
        # if enabled in the configuration
        # This is a no-op if maintenance notifications are not enabled
        self.activate_maint_notifications_handling_if_enabled(check_health=check_health)

        # if a client_name is given, set it
        if self.client_name:
            self.send_command(
                "CLIENT",
                "SETNAME",
                self.client_name,
                check_health=check_health,
            )
            if str_if_bytes(self.read_response()) != "OK":
                raise ConnectionError("Error setting client name")

        # Set the library name and version from driver_info
        try:
            if self.driver_info and self.driver_info.formatted_name:
                self.send_command(
                    "CLIENT",
                    "SETINFO",
                    "LIB-NAME",
                    self.driver_info.formatted_name,
                    check_health=check_health,
                )
                self.read_response()
        except ResponseError:
            pass

        try:
            if self.driver_info and self.driver_info.lib_version:
                self.send_command(
                    "CLIENT",
                    "SETINFO",
                    "LIB-VER",
                    self.driver_info.lib_version,
                    check_health=check_health,
                )
                self.read_response()
        except ResponseError:
            pass

        # if a database is specified, switch to it
        if self.db:
            self.send_command("SELECT", self.db, check_health=check_health)
            if str_if_bytes(self.read_response()) != "OK":
                raise ConnectionError("Invalid Database")

    def disconnect(self, *args, **kwargs):
        "Disconnects from the Redis server"
        self._parser.on_disconnect()

        conn_sock = self._sock
        self._sock = None
        # reset the reconnect flag
        self.reset_should_reconnect()

        if conn_sock is None:
            return

        if os.getpid() == self.pid:
            try:
                conn_sock.shutdown(socket.SHUT_RDWR)
            except (OSError, TypeError):
                pass

        try:
            conn_sock.close()
        except OSError:
            pass

        error = kwargs.get("error")
        failure_count = kwargs.get("failure_count")
        health_check_failed = kwargs.get("health_check_failed")

        if error:
            if health_check_failed:
                close_reason = CloseReason.HEALTHCHECK_FAILED
            else:
                close_reason = CloseReason.ERROR

            if failure_count is not None and failure_count > self.retry.get_retries():
                record_error_count(
                    server_address=self.host,
                    server_port=self.port,
                    network_peer_address=self.host,
                    network_peer_port=self.port,
                    error_type=error,
                    retry_attempts=failure_count,
                )

            record_connection_closed(
                close_reason=close_reason,
                error_type=error,
            )
        else:
            record_connection_closed(
                close_reason=CloseReason.APPLICATION_CLOSE,
            )

        if self.maintenance_state == MaintenanceState.MAINTENANCE:
            # this block will be executed only if the connection was in maintenance state
            # and the connection was closed.
            # The state change won't be applied on connections that are in Moving state
            # because their state and configurations will be handled when the moving ttl expires.
            self.reset_tmp_settings(reset_relaxed_timeout=True)
            self.maintenance_state = MaintenanceState.NONE
            # reset the sets that keep track of received start maint
            # notifications and skipped end maint notifications
            self.reset_received_notifications()

    def mark_for_reconnect(self):
        self._should_reconnect = True

    def should_reconnect(self):
        return self._should_reconnect

    def reset_should_reconnect(self):
        self._should_reconnect = False

    def _send_ping(self):
        """Send PING, expect PONG in return"""
        self.send_command("PING", check_health=False)
        if str_if_bytes(self.read_response()) != "PONG":
            raise ConnectionError("Bad response from PING health check")

    def _ping_failed(self, error, failure_count):
        """Function to call when PING fails"""
        self.disconnect(
            error=error, failure_count=failure_count, health_check_failed=True
        )

    def check_health(self):
        """Check the health of the connection with a PING/PONG"""
        if self.health_check_interval and time.monotonic() > self.next_health_check:
            self.retry.call_with_retry(
                self._send_ping,
                self._ping_failed,
                with_failure_count=True,
            )

    def send_packed_command(self, command, check_health=True):
        """Send an already packed command to the Redis server"""
        if not self._sock:
            self.connect_check_health(check_health=False)
        # guard against health check recursion
        if check_health:
            self.check_health()
        try:
            if isinstance(command, str):
                command = [command]
            for item in command:
                self._sock.sendall(item)
        except socket.timeout:
            self.disconnect()
            raise TimeoutError("Timeout writing to socket")
        except OSError as e:
            self.disconnect()
            if len(e.args) == 1:
                errno, errmsg = "UNKNOWN", e.args[0]
            else:
                errno = e.args[0]
                errmsg = e.args[1]
            raise ConnectionError(f"Error {errno} while writing to socket. {errmsg}.")
        except BaseException:
            # BaseExceptions can be raised when a socket send operation is not
            # finished, e.g. due to a timeout.  Ideally, a caller could then re-try
            # to send un-sent data. However, the send_packed_command() API
            # does not support it so there is no point in keeping the connection open.
            self.disconnect()
            raise

    def send_command(self, *args, **kwargs):
        """Pack and send a command to the Redis server"""
        self.send_packed_command(
            self._command_packer.pack(*args),
            check_health=kwargs.get("check_health", True),
        )

    def can_read(self, timeout=0):
        """Poll the socket to see if there's data that can be read."""
        sock = self._sock
        if not sock:
            self.connect()

        host_error = self._host_error()

        try:
            return self._parser.can_read(timeout)

        except OSError as e:
            self.disconnect()
            raise ConnectionError(f"Error while reading from {host_error}: {e.args}")

    def read_response(
        self,
        disable_decoding=False,
        *,
        disconnect_on_error=True,
        push_request=False,
    ):
        """Read the response from a previously sent command"""

        host_error = self._host_error()

        try:
            if self.protocol in ["3", 3]:
                response = self._parser.read_response(
                    disable_decoding=disable_decoding, push_request=push_request
                )
            else:
                response = self._parser.read_response(disable_decoding=disable_decoding)
        except socket.timeout:
            if disconnect_on_error:
                self.disconnect()
            raise TimeoutError(f"Timeout reading from {host_error}")
        except OSError as e:
            if disconnect_on_error:
                self.disconnect()
            raise ConnectionError(f"Error while reading from {host_error} : {e.args}")
        except BaseException:
            # Also by default close in case of BaseException.  A lot of code
            # relies on this behaviour when doing Command/Response pairs.
            # See #1128.
            if disconnect_on_error:
                self.disconnect()
            raise

        if self.health_check_interval:
            self.next_health_check = time.monotonic() + self.health_check_interval

        if isinstance(response, ResponseError):
            try:
                raise response
            finally:
                del response  # avoid creating ref cycles
        return response

    def pack_command(self, *args):
        """Pack a series of arguments into the Redis protocol"""
        return self._command_packer.pack(*args)

    def pack_commands(self, commands):
        """Pack multiple commands into the Redis protocol"""
        output = []
        pieces = []
        buffer_length = 0
        buffer_cutoff = self._buffer_cutoff

        for cmd in commands:
            for chunk in self._command_packer.pack(*cmd):
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

    def get_protocol(self) -> Union[int, str]:
        return self.protocol

    @property
    def handshake_metadata(self) -> Union[Dict[bytes, bytes], Dict[str, str]]:
        return self._handshake_metadata

    @handshake_metadata.setter
    def handshake_metadata(self, value: Union[Dict[bytes, bytes], Dict[str, str]]):
        self._handshake_metadata = value

    def set_re_auth_token(self, token: TokenInterface):
        self._re_auth_token = token

    def re_auth(self):
        if self._re_auth_token is not None:
            self.send_command(
                "AUTH",
                self._re_auth_token.try_get("oid"),
                self._re_auth_token.get_value(),
            )
            self.read_response()
            self._re_auth_token = None

    def _get_socket(self) -> Optional[socket.socket]:
        return self._sock

    @property
    def socket_timeout(self) -> Optional[Union[float, int]]:
        return self._socket_timeout

    @socket_timeout.setter
    def socket_timeout(self, value: Optional[Union[float, int]]):
        self._socket_timeout = value

    @property
    def socket_connect_timeout(self) -> Optional[Union[float, int]]:
        return self._socket_connect_timeout

    @socket_connect_timeout.setter
    def socket_connect_timeout(self, value: Optional[Union[float, int]]):
        self._socket_connect_timeout = value


class Connection(AbstractConnection):
    "Manages TCP communication to and from a Redis server"

    def __init__(
        self,
        host="localhost",
        port=6379,
        socket_keepalive=False,
        socket_keepalive_options=None,
        socket_type=0,
        **kwargs,
    ):
        self._host = host
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

    def _connect(self):
        "Create a TCP socket connection"
        # we want to mimic what socket.create_connection does to support
        # ipv4/ipv6, but we want to set options prior to calling
        # socket.connect()
        err = None

        for res in socket.getaddrinfo(
            self.host, self.port, self.socket_type, socket.SOCK_STREAM
        ):
            family, socktype, proto, canonname, socket_address = res
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                # TCP_NODELAY
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                # TCP_KEEPALIVE
                if self.socket_keepalive:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for k, v in self.socket_keepalive_options.items():
                        sock.setsockopt(socket.IPPROTO_TCP, k, v)

                # set the socket_connect_timeout before we connect
                sock.settimeout(self.socket_connect_timeout)

                # connect
                sock.connect(socket_address)

                # set the socket_timeout now that we're connected
                sock.settimeout(self.socket_timeout)
                return sock

            except OSError as _:
                err = _
                if sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)  # ensure a clean close
                    except OSError:
                        pass
                    sock.close()

        if err is not None:
            raise err
        raise OSError("socket.getaddrinfo returned an empty list")

    def _host_error(self):
        return f"{self.host}:{self.port}"

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = value


class CacheProxyConnection(MaintNotificationsAbstractConnection, ConnectionInterface):
    DUMMY_CACHE_VALUE = b"foo"
    MIN_ALLOWED_VERSION = "7.4.0"
    DEFAULT_SERVER_NAME = "redis"

    def __init__(
        self,
        conn: ConnectionInterface,
        cache: CacheInterface,
        pool_lock: threading.RLock,
    ):
        self.pid = os.getpid()
        self._conn = conn
        self.retry = self._conn.retry
        self.host = self._conn.host
        self.port = self._conn.port
        self.db = self._conn.db
        self._event_dispatcher = self._conn._event_dispatcher
        self.credential_provider = conn.credential_provider
        self._pool_lock = pool_lock
        self._cache = cache
        self._cache_lock = threading.RLock()
        self._current_command_cache_key = None
        self._current_options = None
        self.register_connect_callback(self._enable_tracking_callback)

        if isinstance(self._conn, MaintNotificationsAbstractConnection):
            MaintNotificationsAbstractConnection.__init__(
                self,
                self._conn.maint_notifications_config,
                self._conn._maint_notifications_pool_handler,
                self._conn.maintenance_state,
                self._conn.maintenance_notification_hash,
                self._conn.host,
                self._conn.socket_timeout,
                self._conn.socket_connect_timeout,
                self._conn._oss_cluster_maint_notifications_handler,
                self._conn._get_parser(),
                event_dispatcher=self._conn.event_dispatcher,
            )

    def repr_pieces(self):
        return self._conn.repr_pieces()

    def register_connect_callback(self, callback):
        self._conn.register_connect_callback(callback)

    def deregister_connect_callback(self, callback):
        self._conn.deregister_connect_callback(callback)

    def set_parser(self, parser_class):
        self._conn.set_parser(parser_class)

    def set_maint_notifications_pool_handler_for_connection(
        self, maint_notifications_pool_handler
    ):
        if isinstance(self._conn, MaintNotificationsAbstractConnection):
            self._conn.set_maint_notifications_pool_handler_for_connection(
                maint_notifications_pool_handler
            )

    def set_maint_notifications_cluster_handler_for_connection(
        self, oss_cluster_maint_notifications_handler
    ):
        if isinstance(self._conn, MaintNotificationsAbstractConnection):
            self._conn.set_maint_notifications_cluster_handler_for_connection(
                oss_cluster_maint_notifications_handler
            )

    def get_protocol(self):
        return self._conn.get_protocol()

    def connect(self):
        self._conn.connect()

        server_name = self._conn.handshake_metadata.get(b"server", None)
        if server_name is None:
            server_name = self._conn.handshake_metadata.get("server", None)
        server_ver = self._conn.handshake_metadata.get(b"version", None)
        if server_ver is None:
            server_ver = self._conn.handshake_metadata.get("version", None)
        if server_ver is None or server_name is None:
            raise ConnectionError("Cannot retrieve information about server version")

        server_ver = ensure_string(server_ver)
        server_name = ensure_string(server_name)

        if (
            server_name != self.DEFAULT_SERVER_NAME
            or compare_versions(server_ver, self.MIN_ALLOWED_VERSION) == 1
        ):
            raise ConnectionError(
                "To maximize compatibility with all Redis products, client-side caching is supported by Redis 7.4 or later"  # noqa: E501
            )

    def on_connect(self):
        self._conn.on_connect()

    def disconnect(self, *args, **kwargs):
        with self._cache_lock:
            self._cache.flush()
        self._conn.disconnect(*args, **kwargs)

    def check_health(self):
        self._conn.check_health()

    def send_packed_command(self, command, check_health=True):
        # TODO: Investigate if it's possible to unpack command
        #  or extract keys from packed command
        self._conn.send_packed_command(command)

    def send_command(self, *args, **kwargs):
        self._process_pending_invalidations()

        with self._cache_lock:
            # Command is write command or not allowed
            # to be cached.
            if not self._cache.is_cachable(
                CacheKey(command=args[0], redis_keys=(), redis_args=())
            ):
                self._current_command_cache_key = None
                self._conn.send_command(*args, **kwargs)
                return

        if kwargs.get("keys") is None:
            raise ValueError("Cannot create cache key.")

        # Creates cache key.
        self._current_command_cache_key = CacheKey(
            command=args[0], redis_keys=tuple(kwargs.get("keys")), redis_args=args
        )

        with self._cache_lock:
            # We have to trigger invalidation processing in case if
            # it was cached by another connection to avoid
            # queueing invalidations in stale connections.
            if self._cache.get(self._current_command_cache_key):
                entry = self._cache.get(self._current_command_cache_key)

                if entry.connection_ref != self._conn:
                    with self._pool_lock:
                        while entry.connection_ref.can_read():
                            entry.connection_ref.read_response(push_request=True)

                return

            # Set temporary entry value to prevent
            # race condition from another connection.
            self._cache.set(
                CacheEntry(
                    cache_key=self._current_command_cache_key,
                    cache_value=self.DUMMY_CACHE_VALUE,
                    status=CacheEntryStatus.IN_PROGRESS,
                    connection_ref=self._conn,
                )
            )

        # Send command over socket only if it's allowed
        # read-only command that not yet cached.
        self._conn.send_command(*args, **kwargs)

    def can_read(self, timeout=0):
        return self._conn.can_read(timeout)

    def read_response(
        self, disable_decoding=False, *, disconnect_on_error=True, push_request=False
    ):
        with self._cache_lock:
            # Check if command response exists in a cache and it's not in progress.
            if self._current_command_cache_key is not None:
                if (
                    self._cache.get(self._current_command_cache_key) is not None
                    and self._cache.get(self._current_command_cache_key).status
                    != CacheEntryStatus.IN_PROGRESS
                ):
                    res = copy.deepcopy(
                        self._cache.get(self._current_command_cache_key).cache_value
                    )
                    self._current_command_cache_key = None
                    record_csc_request(
                        result=CSCResult.HIT,
                    )
                    record_csc_network_saved(
                        bytes_saved=len(res),
                    )
                    return res
                record_csc_request(
                    result=CSCResult.MISS,
                )

        response = self._conn.read_response(
            disable_decoding=disable_decoding,
            disconnect_on_error=disconnect_on_error,
            push_request=push_request,
        )

        with self._cache_lock:
            # Prevent not-allowed command from caching.
            if self._current_command_cache_key is None:
                return response
            # If response is None prevent from caching.
            if response is None:
                self._cache.delete_by_cache_keys([self._current_command_cache_key])
                return response

            cache_entry = self._cache.get(self._current_command_cache_key)

            # Cache only responses that still valid
            # and wasn't invalidated by another connection in meantime.
            if cache_entry is not None:
                cache_entry.status = CacheEntryStatus.VALID
                cache_entry.cache_value = response
                self._cache.set(cache_entry)

            self._current_command_cache_key = None

        return response

    def pack_command(self, *args):
        return self._conn.pack_command(*args)

    def pack_commands(self, commands):
        return self._conn.pack_commands(commands)

    @property
    def handshake_metadata(self) -> Union[Dict[bytes, bytes], Dict[str, str]]:
        return self._conn.handshake_metadata

    def set_re_auth_token(self, token: TokenInterface):
        self._conn.set_re_auth_token(token)

    def re_auth(self):
        self._conn.re_auth()

    def mark_for_reconnect(self):
        self._conn.mark_for_reconnect()

    def should_reconnect(self):
        return self._conn.should_reconnect()

    def reset_should_reconnect(self):
        self._conn.reset_should_reconnect()

    @property
    def host(self) -> str:
        return self._conn.host

    @host.setter
    def host(self, value: str):
        self._conn.host = value

    @property
    def socket_timeout(self) -> Optional[Union[float, int]]:
        return self._conn.socket_timeout

    @socket_timeout.setter
    def socket_timeout(self, value: Optional[Union[float, int]]):
        self._conn.socket_timeout = value

    @property
    def socket_connect_timeout(self) -> Optional[Union[float, int]]:
        return self._conn.socket_connect_timeout

    @socket_connect_timeout.setter
    def socket_connect_timeout(self, value: Optional[Union[float, int]]):
        self._conn.socket_connect_timeout = value

    @property
    def _maint_notifications_connection_handler(
        self,
    ) -> Optional[MaintNotificationsConnectionHandler]:
        if isinstance(self._conn, MaintNotificationsAbstractConnection):
            return self._conn._maint_notifications_connection_handler

    @_maint_notifications_connection_handler.setter
    def _maint_notifications_connection_handler(
        self, value: Optional[MaintNotificationsConnectionHandler]
    ):
        self._conn._maint_notifications_connection_handler = value

    def _get_socket(self) -> Optional[socket.socket]:
        if isinstance(self._conn, MaintNotificationsAbstractConnection):
            return self._conn._get_socket()
        else:
            raise NotImplementedError(
                "Maintenance notifications are not supported by this connection type"
            )

    def _get_maint_notifications_connection_instance(
        self, connection
    ) -> MaintNotificationsAbstractConnection:
        """
        Validate that connection instance supports maintenance notifications.
        With this helper method we ensure that we are working
        with the correct connection type.
        After twe validate that connection instance supports maintenance notifications
        we can safely return the connection instance
        as MaintNotificationsAbstractConnection.
        """
        if not isinstance(connection, MaintNotificationsAbstractConnection):
            raise NotImplementedError(
                "Maintenance notifications are not supported by this connection type"
            )
        else:
            return connection

    @property
    def maintenance_state(self) -> MaintenanceState:
        con = self._get_maint_notifications_connection_instance(self._conn)
        return con.maintenance_state

    @maintenance_state.setter
    def maintenance_state(self, state: MaintenanceState):
        con = self._get_maint_notifications_connection_instance(self._conn)
        con.maintenance_state = state

    def getpeername(self):
        con = self._get_maint_notifications_connection_instance(self._conn)
        return con.getpeername()

    def get_resolved_ip(self):
        con = self._get_maint_notifications_connection_instance(self._conn)
        return con.get_resolved_ip()

    def update_current_socket_timeout(self, relaxed_timeout: Optional[float] = None):
        con = self._get_maint_notifications_connection_instance(self._conn)
        con.update_current_socket_timeout(relaxed_timeout)

    def set_tmp_settings(
        self,
        tmp_host_address: Optional[str] = None,
        tmp_relaxed_timeout: Optional[float] = None,
    ):
        con = self._get_maint_notifications_connection_instance(self._conn)
        con.set_tmp_settings(tmp_host_address, tmp_relaxed_timeout)

    def reset_tmp_settings(
        self,
        reset_host_address: bool = False,
        reset_relaxed_timeout: bool = False,
    ):
        con = self._get_maint_notifications_connection_instance(self._conn)
        con.reset_tmp_settings(reset_host_address, reset_relaxed_timeout)

    def _connect(self):
        self._conn._connect()

    def _host_error(self):
        self._conn._host_error()

    def _enable_tracking_callback(self, conn: ConnectionInterface) -> None:
        conn.send_command("CLIENT", "TRACKING", "ON")
        conn.read_response()
        conn._parser.set_invalidation_push_handler(self._on_invalidation_callback)

    def _process_pending_invalidations(self):
        while self.can_read():
            self._conn.read_response(push_request=True)

    def _on_invalidation_callback(self, data: List[Union[str, Optional[List[bytes]]]]):
        with self._cache_lock:
            # Flush cache when DB flushed on server-side
            if data[1] is None:
                self._cache.flush()
            else:
                keys_deleted = self._cache.delete_by_redis_keys(data[1])

                if len(keys_deleted) > 0:
                    record_csc_eviction(
                        count=len(keys_deleted),
                        reason=CSCReason.INVALIDATION,
                    )


class SSLConnection(Connection):
    """Manages SSL connections to and from the Redis server(s).
    This class extends the Connection class, adding SSL functionality, and making
    use of ssl.SSLContext (https://docs.python.org/3/library/ssl.html#ssl.SSLContext)
    """  # noqa

    def __init__(
        self,
        ssl_keyfile=None,
        ssl_certfile=None,
        ssl_cert_reqs="required",
        ssl_include_verify_flags: Optional[List["VerifyFlags"]] = None,
        ssl_exclude_verify_flags: Optional[List["VerifyFlags"]] = None,
        ssl_ca_certs=None,
        ssl_ca_data=None,
        ssl_check_hostname=True,
        ssl_ca_path=None,
        ssl_password=None,
        ssl_validate_ocsp=False,
        ssl_validate_ocsp_stapled=False,
        ssl_ocsp_context=None,
        ssl_ocsp_expected_cert=None,
        ssl_min_version=None,
        ssl_ciphers=None,
        **kwargs,
    ):
        """Constructor

        Args:
            ssl_keyfile: Path to an ssl private key. Defaults to None.
            ssl_certfile: Path to an ssl certificate. Defaults to None.
            ssl_cert_reqs: The string value for the SSLContext.verify_mode (none, optional, required),
                           or an ssl.VerifyMode. Defaults to "required".
            ssl_include_verify_flags: A list of flags to be included in the SSLContext.verify_flags. Defaults to None.
            ssl_exclude_verify_flags: A list of flags to be excluded from the SSLContext.verify_flags. Defaults to None.
            ssl_ca_certs: The path to a file of concatenated CA certificates in PEM format. Defaults to None.
            ssl_ca_data: Either an ASCII string of one or more PEM-encoded certificates or a bytes-like object of DER-encoded certificates.
            ssl_check_hostname: If set, match the hostname during the SSL handshake. Defaults to True.
            ssl_ca_path: The path to a directory containing several CA certificates in PEM format. Defaults to None.
            ssl_password: Password for unlocking an encrypted private key. Defaults to None.

            ssl_validate_ocsp: If set, perform a full ocsp validation (i.e not a stapled verification)
            ssl_validate_ocsp_stapled: If set, perform a validation on a stapled ocsp response
            ssl_ocsp_context: A fully initialized OpenSSL.SSL.Context object to be used in verifying the ssl_ocsp_expected_cert
            ssl_ocsp_expected_cert: A PEM armoured string containing the expected certificate to be returned from the ocsp verification service.
            ssl_min_version: The lowest supported SSL version. It affects the supported SSL versions of the SSLContext. None leaves the default provided by ssl module.
            ssl_ciphers: A string listing the ciphers that are allowed to be used. Defaults to None, which means that the default ciphers are used. See https://docs.python.org/3/library/ssl.html#ssl.SSLContext.set_ciphers for more information.

        Raises:
            RedisError
        """  # noqa
        if not SSL_AVAILABLE:
            raise RedisError("Python wasn't built with SSL support")

        self.keyfile = ssl_keyfile
        self.certfile = ssl_certfile
        if ssl_cert_reqs is None:
            ssl_cert_reqs = ssl.CERT_NONE
        elif isinstance(ssl_cert_reqs, str):
            CERT_REQS = {  # noqa: N806
                "none": ssl.CERT_NONE,
                "optional": ssl.CERT_OPTIONAL,
                "required": ssl.CERT_REQUIRED,
            }
            if ssl_cert_reqs not in CERT_REQS:
                raise RedisError(
                    f"Invalid SSL Certificate Requirements Flag: {ssl_cert_reqs}"
                )
            ssl_cert_reqs = CERT_REQS[ssl_cert_reqs]
        self.cert_reqs = ssl_cert_reqs
        self.ssl_include_verify_flags = ssl_include_verify_flags
        self.ssl_exclude_verify_flags = ssl_exclude_verify_flags
        self.ca_certs = ssl_ca_certs
        self.ca_data = ssl_ca_data
        self.ca_path = ssl_ca_path
        self.check_hostname = (
            ssl_check_hostname if self.cert_reqs != ssl.CERT_NONE else False
        )
        self.certificate_password = ssl_password
        self.ssl_validate_ocsp = ssl_validate_ocsp
        self.ssl_validate_ocsp_stapled = ssl_validate_ocsp_stapled
        self.ssl_ocsp_context = ssl_ocsp_context
        self.ssl_ocsp_expected_cert = ssl_ocsp_expected_cert
        self.ssl_min_version = ssl_min_version
        self.ssl_ciphers = ssl_ciphers
        super().__init__(**kwargs)

    def _connect(self):
        """
        Wrap the socket with SSL support, handling potential errors.
        """
        sock = super()._connect()
        try:
            return self._wrap_socket_with_ssl(sock)
        except (OSError, RedisError):
            sock.close()
            raise

    def _wrap_socket_with_ssl(self, sock):
        """
        Wraps the socket with SSL support.

        Args:
            sock: The plain socket to wrap with SSL.

        Returns:
            An SSL wrapped socket.
        """
        context = ssl.create_default_context()
        context.check_hostname = self.check_hostname
        context.verify_mode = self.cert_reqs
        if self.ssl_include_verify_flags:
            for flag in self.ssl_include_verify_flags:
                context.verify_flags |= flag
        if self.ssl_exclude_verify_flags:
            for flag in self.ssl_exclude_verify_flags:
                context.verify_flags &= ~flag
        if self.certfile or self.keyfile:
            context.load_cert_chain(
                certfile=self.certfile,
                keyfile=self.keyfile,
                password=self.certificate_password,
            )
        if (
            self.ca_certs is not None
            or self.ca_path is not None
            or self.ca_data is not None
        ):
            context.load_verify_locations(
                cafile=self.ca_certs, capath=self.ca_path, cadata=self.ca_data
            )
        if self.ssl_min_version is not None:
            context.minimum_version = self.ssl_min_version
        if self.ssl_ciphers:
            context.set_ciphers(self.ssl_ciphers)
        if self.ssl_validate_ocsp is True and CRYPTOGRAPHY_AVAILABLE is False:
            raise RedisError("cryptography is not installed.")

        if self.ssl_validate_ocsp_stapled and self.ssl_validate_ocsp:
            raise RedisError(
                "Either an OCSP staple or pure OCSP connection must be validated "
                "- not both."
            )

        sslsock = context.wrap_socket(sock, server_hostname=self.host)

        # validation for the stapled case
        if self.ssl_validate_ocsp_stapled:
            import OpenSSL

            from .ocsp import ocsp_staple_verifier

            # if a context is provided use it - otherwise, a basic context
            if self.ssl_ocsp_context is None:
                staple_ctx = OpenSSL.SSL.Context(OpenSSL.SSL.SSLv23_METHOD)
                staple_ctx.use_certificate_file(self.certfile)
                staple_ctx.use_privatekey_file(self.keyfile)
            else:
                staple_ctx = self.ssl_ocsp_context

            staple_ctx.set_ocsp_client_callback(
                ocsp_staple_verifier, self.ssl_ocsp_expected_cert
            )

            #  need another socket
            con = OpenSSL.SSL.Connection(staple_ctx, socket.socket())
            con.request_ocsp()
            con.connect((self.host, self.port))
            con.do_handshake()
            con.shutdown()
            return sslsock

        # pure ocsp validation
        if self.ssl_validate_ocsp is True and CRYPTOGRAPHY_AVAILABLE:
            from .ocsp import OCSPVerifier

            o = OCSPVerifier(sslsock, self.host, self.port, self.ca_certs)
            if o.is_valid():
                return sslsock
            else:
                raise ConnectionError("ocsp validation error")
        return sslsock


class UnixDomainSocketConnection(AbstractConnection):
    "Manages UDS communication to and from a Redis server"

    def __init__(self, path="", socket_timeout=None, **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.socket_timeout = socket_timeout

    def repr_pieces(self):
        pieces = [("path", self.path), ("db", self.db)]
        if self.client_name:
            pieces.append(("client_name", self.client_name))
        return pieces

    def _connect(self):
        "Create a Unix domain socket connection"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.socket_connect_timeout)
        try:
            sock.connect(self.path)
        except OSError:
            # Prevent ResourceWarnings for unclosed sockets.
            try:
                sock.shutdown(socket.SHUT_RDWR)  # ensure a clean close
            except OSError:
                pass
            sock.close()
            raise
        sock.settimeout(self.socket_timeout)
        return sock

    def _host_error(self):
        return self.path


FALSE_STRINGS = ("0", "F", "FALSE", "N", "NO")


def to_bool(value):
    if value is None or value == "":
        return None
    if isinstance(value, str) and value.upper() in FALSE_STRINGS:
        return False
    return bool(value)


def parse_ssl_verify_flags(value):
    # flags are passed in as a string representation of a list,
    # e.g. VERIFY_X509_STRICT, VERIFY_X509_PARTIAL_CHAIN
    verify_flags_str = value.replace("[", "").replace("]", "")

    verify_flags = []
    for flag in verify_flags_str.split(","):
        flag = flag.strip()
        if not hasattr(VerifyFlags, flag):
            raise ValueError(f"Invalid ssl verify flag: {flag}")
        verify_flags.append(getattr(VerifyFlags, flag))
    return verify_flags


URL_QUERY_ARGUMENT_PARSERS = {
    "db": int,
    "socket_timeout": float,
    "socket_connect_timeout": float,
    "socket_keepalive": to_bool,
    "retry_on_timeout": to_bool,
    "retry_on_error": list,
    "max_connections": int,
    "health_check_interval": int,
    "ssl_check_hostname": to_bool,
    "ssl_include_verify_flags": parse_ssl_verify_flags,
    "ssl_exclude_verify_flags": parse_ssl_verify_flags,
    "timeout": float,
}


def parse_url(url):
    if not (
        url.startswith("redis://")
        or url.startswith("rediss://")
        or url.startswith("unix://")
    ):
        raise ValueError(
            "Redis URL must specify one of the following "
            "schemes (redis://, rediss://, unix://)"
        )

    url = urlparse(url)
    kwargs = {}

    for name, value in parse_qs(url.query).items():
        if value and len(value) > 0:
            value = unquote(value[0])
            parser = URL_QUERY_ARGUMENT_PARSERS.get(name)
            if parser:
                try:
                    kwargs[name] = parser(value)
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid value for '{name}' in connection URL.")
            else:
                kwargs[name] = value

    if url.username:
        kwargs["username"] = unquote(url.username)
    if url.password:
        kwargs["password"] = unquote(url.password)

    # We only support redis://, rediss:// and unix:// schemes.
    if url.scheme == "unix":
        if url.path:
            kwargs["path"] = unquote(url.path)
        kwargs["connection_class"] = UnixDomainSocketConnection

    else:  # implied:  url.scheme in ("redis", "rediss"):
        if url.hostname:
            kwargs["host"] = unquote(url.hostname)
        if url.port:
            kwargs["port"] = int(url.port)

        # If there's a path argument, use it as the db argument if a
        # querystring value wasn't specified
        if url.path and "db" not in kwargs:
            try:
                kwargs["db"] = int(unquote(url.path).replace("/", ""))
            except (AttributeError, ValueError):
                pass

        if url.scheme == "rediss":
            kwargs["connection_class"] = SSLConnection

    return kwargs


_CP = TypeVar("_CP", bound="ConnectionPool")


class ConnectionPoolInterface(ABC):
    @abstractmethod
    def get_protocol(self):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    @deprecated_args(
        args_to_warn=["*"],
        reason="Use get_connection() without args instead",
        version="5.3.0",
    )
    def get_connection(
        self, command_name: Optional[str], *keys, **options
    ) -> ConnectionInterface:
        pass

    @abstractmethod
    def get_encoder(self):
        pass

    @abstractmethod
    def release(self, connection: ConnectionInterface):
        pass

    @abstractmethod
    def disconnect(self, inuse_connections: bool = True):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def set_retry(self, retry: Retry):
        pass

    @abstractmethod
    def re_auth_callback(self, token: TokenInterface):
        pass

    @abstractmethod
    def get_connection_count(self) -> list[tuple[int, dict]]:
        """
        Returns a connection count (both idle and in use).
        """
        pass


class MaintNotificationsAbstractConnectionPool:
    """
    Abstract class for handling maintenance notifications logic.
    This class is mixed into the ConnectionPool classes.

    This class is not intended to be used directly!

    All logic related to maintenance notifications and
    connection pool handling is encapsulated in this class.
    """

    def __init__(
        self,
        maint_notifications_config: Optional[MaintNotificationsConfig] = None,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
        **kwargs,
    ):
        # Initialize maintenance notifications
        is_protocol_supported = check_protocol_version(kwargs.get("protocol"), 3)

        if maint_notifications_config is None and is_protocol_supported:
            maint_notifications_config = MaintNotificationsConfig()

        if maint_notifications_config and maint_notifications_config.enabled:
            if not is_protocol_supported:
                raise RedisError(
                    "Maintenance notifications handlers on connection are only supported with RESP version 3"
                )

            self._event_dispatcher = kwargs.get("event_dispatcher", None)
            if self._event_dispatcher is None:
                self._event_dispatcher = EventDispatcher()

            self._maint_notifications_pool_handler = MaintNotificationsPoolHandler(
                self, maint_notifications_config
            )
            if oss_cluster_maint_notifications_handler:
                self._oss_cluster_maint_notifications_handler = (
                    oss_cluster_maint_notifications_handler
                )
                self._update_connection_kwargs_for_maint_notifications(
                    oss_cluster_maint_notifications_handler=self._oss_cluster_maint_notifications_handler
                )
                self._maint_notifications_pool_handler = None
            else:
                self._oss_cluster_maint_notifications_handler = None
                self._maint_notifications_pool_handler = MaintNotificationsPoolHandler(
                    self, maint_notifications_config
                )

                self._update_connection_kwargs_for_maint_notifications(
                    maint_notifications_pool_handler=self._maint_notifications_pool_handler
                )
        else:
            self._maint_notifications_pool_handler = None
            self._oss_cluster_maint_notifications_handler = None

    @property
    @abstractmethod
    def connection_kwargs(self) -> Dict[str, Any]:
        pass

    @connection_kwargs.setter
    @abstractmethod
    def connection_kwargs(self, value: Dict[str, Any]):
        pass

    @abstractmethod
    def _get_pool_lock(self) -> threading.RLock:
        pass

    @abstractmethod
    def _get_free_connections(self) -> Iterable["MaintNotificationsAbstractConnection"]:
        pass

    @abstractmethod
    def _get_in_use_connections(
        self,
    ) -> Iterable["MaintNotificationsAbstractConnection"]:
        pass

    def maint_notifications_enabled(self):
        """
        Returns:
            True if the maintenance notifications are enabled, False otherwise.
            The maintenance notifications config is stored in the pool handler.
            If the pool handler is not set, the maintenance notifications are not enabled.
        """
        if self._oss_cluster_maint_notifications_handler:
            maint_notifications_config = (
                self._oss_cluster_maint_notifications_handler.config
            )
        else:
            maint_notifications_config = (
                self._maint_notifications_pool_handler.config
                if self._maint_notifications_pool_handler
                else None
            )

        return maint_notifications_config and maint_notifications_config.enabled

    def update_maint_notifications_config(
        self,
        maint_notifications_config: MaintNotificationsConfig,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
    ):
        """
        Updates the maintenance notifications configuration.
        This method should be called only if the pool was created
        without enabling the maintenance notifications and
        in a later point in time maintenance notifications
        are requested to be enabled.
        """
        if (
            self.maint_notifications_enabled()
            and not maint_notifications_config.enabled
        ):
            raise ValueError(
                "Cannot disable maintenance notifications after enabling them"
            )
        if oss_cluster_maint_notifications_handler:
            self._oss_cluster_maint_notifications_handler = (
                oss_cluster_maint_notifications_handler
            )
        else:
            # first update pool settings
            if not self._maint_notifications_pool_handler:
                self._maint_notifications_pool_handler = MaintNotificationsPoolHandler(
                    self, maint_notifications_config
                )
            else:
                self._maint_notifications_pool_handler.config = (
                    maint_notifications_config
                )

        # then update connection kwargs and existing connections
        self._update_connection_kwargs_for_maint_notifications(
            maint_notifications_pool_handler=self._maint_notifications_pool_handler,
            oss_cluster_maint_notifications_handler=self._oss_cluster_maint_notifications_handler,
        )
        self._update_maint_notifications_configs_for_connections(
            maint_notifications_pool_handler=self._maint_notifications_pool_handler,
            oss_cluster_maint_notifications_handler=self._oss_cluster_maint_notifications_handler,
        )

    def _update_connection_kwargs_for_maint_notifications(
        self,
        maint_notifications_pool_handler: Optional[
            MaintNotificationsPoolHandler
        ] = None,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
    ):
        """
        Update the connection kwargs for all future connections.
        """
        if not self.maint_notifications_enabled():
            return
        if maint_notifications_pool_handler:
            self.connection_kwargs.update(
                {
                    "maint_notifications_pool_handler": maint_notifications_pool_handler,
                    "maint_notifications_config": maint_notifications_pool_handler.config,
                }
            )
        if oss_cluster_maint_notifications_handler:
            self.connection_kwargs.update(
                {
                    "oss_cluster_maint_notifications_handler": oss_cluster_maint_notifications_handler,
                    "maint_notifications_config": oss_cluster_maint_notifications_handler.config,
                }
            )

        # Store original connection parameters for maintenance notifications.
        if self.connection_kwargs.get("orig_host_address", None) is None:
            # If orig_host_address is None it means we haven't
            # configured the original values yet
            self.connection_kwargs.update(
                {
                    "orig_host_address": self.connection_kwargs.get("host"),
                    "orig_socket_timeout": self.connection_kwargs.get(
                        "socket_timeout", None
                    ),
                    "orig_socket_connect_timeout": self.connection_kwargs.get(
                        "socket_connect_timeout", None
                    ),
                }
            )

    def _update_maint_notifications_configs_for_connections(
        self,
        maint_notifications_pool_handler: Optional[
            MaintNotificationsPoolHandler
        ] = None,
        oss_cluster_maint_notifications_handler: Optional[
            OSSMaintNotificationsHandler
        ] = None,
    ):
        """Update the maintenance notifications config for all connections in the pool."""
        with self._get_pool_lock():
            for conn in self._get_free_connections():
                if oss_cluster_maint_notifications_handler:
                    # set cluster handler for conn
                    conn.set_maint_notifications_cluster_handler_for_connection(
                        oss_cluster_maint_notifications_handler
                    )
                    conn.maint_notifications_config = (
                        oss_cluster_maint_notifications_handler.config
                    )
                elif maint_notifications_pool_handler:
                    conn.set_maint_notifications_pool_handler_for_connection(
                        maint_notifications_pool_handler
                    )
                    conn.maint_notifications_config = (
                        maint_notifications_pool_handler.config
                    )
                else:
                    raise ValueError(
                        "Either maint_notifications_pool_handler or oss_cluster_maint_notifications_handler must be set"
                    )
                conn.disconnect()
            for conn in self._get_in_use_connections():
                if oss_cluster_maint_notifications_handler:
                    conn.maint_notifications_config = (
                        oss_cluster_maint_notifications_handler.config
                    )
                    conn._configure_maintenance_notifications(
                        oss_cluster_maint_notifications_handler=oss_cluster_maint_notifications_handler
                    )
                elif maint_notifications_pool_handler:
                    conn.set_maint_notifications_pool_handler_for_connection(
                        maint_notifications_pool_handler
                    )
                    conn.maint_notifications_config = (
                        maint_notifications_pool_handler.config
                    )
                else:
                    raise ValueError(
                        "Either maint_notifications_pool_handler or oss_cluster_maint_notifications_handler must be set"
                    )
                conn.mark_for_reconnect()

    def _should_update_connection(
        self,
        conn: "MaintNotificationsAbstractConnection",
        matching_pattern: Literal[
            "connected_address", "configured_address", "notification_hash"
        ] = "connected_address",
        matching_address: Optional[str] = None,
        matching_notification_hash: Optional[int] = None,
    ) -> bool:
        """
        Check if the connection should be updated based on the matching criteria.
        """
        if matching_pattern == "connected_address":
            if matching_address and conn.getpeername() != matching_address:
                return False
        elif matching_pattern == "configured_address":
            if matching_address and conn.host != matching_address:
                return False
        elif matching_pattern == "notification_hash":
            if (
                matching_notification_hash
                and conn.maintenance_notification_hash != matching_notification_hash
            ):
                return False
        return True

    def update_connection_settings(
        self,
        conn: "MaintNotificationsAbstractConnection",
        state: Optional["MaintenanceState"] = None,
        maintenance_notification_hash: Optional[int] = None,
        host_address: Optional[str] = None,
        relaxed_timeout: Optional[float] = None,
        update_notification_hash: bool = False,
        reset_host_address: bool = False,
        reset_relaxed_timeout: bool = False,
    ):
        """
        Update the settings for a single connection.
        """
        if state:
            conn.maintenance_state = state

        if update_notification_hash:
            # update the notification hash only if requested
            conn.maintenance_notification_hash = maintenance_notification_hash

        if host_address is not None:
            conn.set_tmp_settings(tmp_host_address=host_address)

        if relaxed_timeout is not None:
            conn.set_tmp_settings(tmp_relaxed_timeout=relaxed_timeout)

        if reset_relaxed_timeout or reset_host_address:
            conn.reset_tmp_settings(
                reset_host_address=reset_host_address,
                reset_relaxed_timeout=reset_relaxed_timeout,
            )

        conn.update_current_socket_timeout(relaxed_timeout)

    def update_connections_settings(
        self,
        state: Optional["MaintenanceState"] = None,
        maintenance_notification_hash: Optional[int] = None,
        host_address: Optional[str] = None,
        relaxed_timeout: Optional[float] = None,
        matching_address: Optional[str] = None,
        matching_notification_hash: Optional[int] = None,
        matching_pattern: Literal[
            "connected_address", "configured_address", "notification_hash"
        ] = "connected_address",
        update_notification_hash: bool = False,
        reset_host_address: bool = False,
        reset_relaxed_timeout: bool = False,
        include_free_connections: bool = True,
    ):
        """
        Update the settings for all matching connections in the pool.

        This method does not create new connections.
        This method does not affect the connection kwargs.

        :param state: The maintenance state to set for the connection.
        :param maintenance_notification_hash: The hash of the maintenance notification
                                               to set for the connection.
        :param host_address: The host address to set for the connection.
        :param relaxed_timeout: The relaxed timeout to set for the connection.
        :param matching_address: The address to match for the connection.
        :param matching_notification_hash: The notification hash to match for the connection.
        :param matching_pattern: The pattern to match for the connection.
        :param update_notification_hash: Whether to update the notification hash for the connection.
        :param reset_host_address: Whether to reset the host address to the original address.
        :param reset_relaxed_timeout: Whether to reset the relaxed timeout to the original timeout.
        :param include_free_connections: Whether to include free/available connections.
        """
        with self._get_pool_lock():
            for conn in self._get_in_use_connections():
                if self._should_update_connection(
                    conn,
                    matching_pattern,
                    matching_address,
                    matching_notification_hash,
                ):
                    self.update_connection_settings(
                        conn,
                        state=state,
                        maintenance_notification_hash=maintenance_notification_hash,
                        host_address=host_address,
                        relaxed_timeout=relaxed_timeout,
                        update_notification_hash=update_notification_hash,
                        reset_host_address=reset_host_address,
                        reset_relaxed_timeout=reset_relaxed_timeout,
                    )

            if include_free_connections:
                for conn in self._get_free_connections():
                    if self._should_update_connection(
                        conn,
                        matching_pattern,
                        matching_address,
                        matching_notification_hash,
                    ):
                        self.update_connection_settings(
                            conn,
                            state=state,
                            maintenance_notification_hash=maintenance_notification_hash,
                            host_address=host_address,
                            relaxed_timeout=relaxed_timeout,
                            update_notification_hash=update_notification_hash,
                            reset_host_address=reset_host_address,
                            reset_relaxed_timeout=reset_relaxed_timeout,
                        )

    def update_connection_kwargs(
        self,
        **kwargs,
    ):
        """
        Update the connection kwargs for all future connections.

        This method updates the connection kwargs for all future connections created by the pool.
        Existing connections are not affected.
        """
        self.connection_kwargs.update(kwargs)

    def update_active_connections_for_reconnect(
        self,
        moving_address_src: Optional[str] = None,
    ):
        """
        Mark all active connections for reconnect.
        This is used when a cluster node is migrated to a different address.

        :param moving_address_src: The address of the node that is being moved.
        """
        with self._get_pool_lock():
            for conn in self._get_in_use_connections():
                if self._should_update_connection(
                    conn, "connected_address", moving_address_src
                ):
                    conn.mark_for_reconnect()

    def disconnect_free_connections(
        self,
        moving_address_src: Optional[str] = None,
    ):
        """
        Disconnect all free/available connections.
        This is used when a cluster node is migrated to a different address.

        :param moving_address_src: The address of the node that is being moved.
        """
        with self._get_pool_lock():
            for conn in self._get_free_connections():
                if self._should_update_connection(
                    conn, "connected_address", moving_address_src
                ):
                    conn.disconnect()


class ConnectionPool(MaintNotificationsAbstractConnectionPool, ConnectionPoolInterface):
    """
    Create a connection pool. ``If max_connections`` is set, then this
    object raises :py:class:`~redis.exceptions.ConnectionError` when the pool's
    limit is reached.

    By default, TCP connections are created unless ``connection_class``
    is specified. Use class:`.UnixDomainSocketConnection` for
    unix sockets.
    :py:class:`~redis.SSLConnection` can be used for SSL enabled connections.

    If ``maint_notifications_config`` is provided, the connection pool will support
    maintenance notifications.
    Maintenance notifications are supported only with RESP3.
    If the ``maint_notifications_config`` is not provided but the ``protocol`` is 3,
    the maintenance notifications will be enabled by default.

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

        if "connection_class" in kwargs:
            url_options["connection_class"] = kwargs["connection_class"]

        kwargs.update(url_options)
        return cls(**kwargs)

    def __init__(
        self,
        connection_class=Connection,
        max_connections: Optional[int] = None,
        cache_factory: Optional[CacheFactoryInterface] = None,
        maint_notifications_config: Optional[MaintNotificationsConfig] = None,
        **connection_kwargs,
    ):
        max_connections = max_connections or 2**31
        if not isinstance(max_connections, int) or max_connections < 0:
            raise ValueError('"max_connections" must be a positive integer')

        self.connection_class = connection_class
        self._connection_kwargs = connection_kwargs
        self.max_connections = max_connections
        self.cache = None
        self._cache_factory = cache_factory

        self._event_dispatcher = self._connection_kwargs.get("event_dispatcher", None)
        if self._event_dispatcher is None:
            self._event_dispatcher = EventDispatcher()

        if connection_kwargs.get("cache_config") or connection_kwargs.get("cache"):
            if not check_protocol_version(self._connection_kwargs.get("protocol"), 3):
                raise RedisError("Client caching is only supported with RESP version 3")

            cache = self._connection_kwargs.get("cache")

            if cache is not None:
                if not isinstance(cache, CacheInterface):
                    raise ValueError("Cache must implement CacheInterface")

                self.cache = cache
            else:
                if self._cache_factory is not None:
                    self.cache = CacheProxy(self._cache_factory.get_cache())
                else:
                    self.cache = CacheFactory(
                        self._connection_kwargs.get("cache_config")
                    ).get_cache()

            init_csc_items()
            register_csc_items_callback(
                callback=lambda: self.cache.size,
                pool_name=get_pool_name(self),
            )

        connection_kwargs.pop("cache", None)
        connection_kwargs.pop("cache_config", None)

        # a lock to protect the critical section in _checkpid().
        # this lock is acquired when the process id changes, such as
        # after a fork. during this time, multiple threads in the child
        # process could attempt to acquire this lock. the first thread
        # to acquire the lock will reset the data structures and lock
        # object of this pool. subsequent threads acquiring this lock
        # will notice the first thread already did the work and simply
        # release the lock.

        self._fork_lock = threading.RLock()
        self._lock = threading.RLock()

        # Generate unique pool ID for observability (matches go-redis behavior)
        import secrets

        self._pool_id = secrets.token_hex(4)

        MaintNotificationsAbstractConnectionPool.__init__(
            self,
            maint_notifications_config=maint_notifications_config,
            **connection_kwargs,
        )

        self.reset()

    def __repr__(self) -> str:
        conn_kwargs = ",".join([f"{k}={v}" for k, v in self.connection_kwargs.items()])
        return (
            f"<{self.__class__.__module__}.{self.__class__.__name__}"
            f"(<{self.connection_class.__module__}.{self.connection_class.__name__}"
            f"({conn_kwargs})>)>"
        )

    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        return self._connection_kwargs

    @connection_kwargs.setter
    def connection_kwargs(self, value: Dict[str, Any]):
        self._connection_kwargs = value

    def get_protocol(self):
        """
        Returns:
            The RESP protocol version, or ``None`` if the protocol is not specified,
            in which case the server default will be used.
        """
        return self.connection_kwargs.get("protocol", None)

    def reset(self) -> None:
        self._created_connections = 0
        self._available_connections = []
        self._in_use_connections = set()

        # this must be the last operation in this method. while reset() is
        # called when holding _fork_lock, other threads in this process
        # can call _checkpid() which compares self.pid and os.getpid() without
        # holding any lock (for performance reasons). keeping this assignment
        # as the last operation ensures that those other threads will also
        # notice a pid difference and block waiting for the first thread to
        # release _fork_lock. when each of these threads eventually acquire
        # _fork_lock, they will notice that another thread already called
        # reset() and they will immediately release _fork_lock and continue on.
        self.pid = os.getpid()

    def _checkpid(self) -> None:
        # _checkpid() attempts to keep ConnectionPool fork-safe on modern
        # systems. this is called by all ConnectionPool methods that
        # manipulate the pool's state such as get_connection() and release().
        #
        # _checkpid() determines whether the process has forked by comparing
        # the current process id to the process id saved on the ConnectionPool
        # instance. if these values are the same, _checkpid() simply returns.
        #
        # when the process ids differ, _checkpid() assumes that the process
        # has forked and that we're now running in the child process. the child
        # process cannot use the parent's file descriptors (e.g., sockets).
        # therefore, when _checkpid() sees the process id change, it calls
        # reset() in order to reinitialize the child's ConnectionPool. this
        # will cause the child to make all new connection objects.
        #
        # _checkpid() is protected by self._fork_lock to ensure that multiple
        # threads in the child process do not call reset() multiple times.
        #
        # there is an extremely small chance this could fail in the following
        # scenario:
        #   1. process A calls _checkpid() for the first time and acquires
        #      self._fork_lock.
        #   2. while holding self._fork_lock, process A forks (the fork()
        #      could happen in a different thread owned by process A)
        #   3. process B (the forked child process) inherits the
        #      ConnectionPool's state from the parent. that state includes
        #      a locked _fork_lock. process B will not be notified when
        #      process A releases the _fork_lock and will thus never be
        #      able to acquire the _fork_lock.
        #
        # to mitigate this possible deadlock, _checkpid() will only wait 5
        # seconds to acquire _fork_lock. if _fork_lock cannot be acquired in
        # that time it is assumed that the child is deadlocked and a
        # redis.ChildDeadlockedError error is raised.
        if self.pid != os.getpid():
            acquired = self._fork_lock.acquire(timeout=5)
            if not acquired:
                raise ChildDeadlockedError
            # reset() the instance for the new process if another thread
            # hasn't already done so
            try:
                if self.pid != os.getpid():
                    self.reset()
            finally:
                self._fork_lock.release()

    @deprecated_args(
        args_to_warn=["*"],
        reason="Use get_connection() without args instead",
        version="5.3.0",
    )
    def get_connection(self, command_name=None, *keys, **options) -> "Connection":
        "Get a connection from the pool"

        # Start timing for observability
        self._checkpid()
        is_created = False

        with self._lock:
            try:
                connection = self._available_connections.pop()
            except IndexError:
                # Start timing for observability
                start_time_created = time.monotonic()

                connection = self.make_connection()
                is_created = True
            self._in_use_connections.add(connection)

        try:
            # ensure this connection is connected to Redis
            connection.connect()
            # connections that the pool provides should be ready to send
            # a command. if not, the connection was either returned to the
            # pool before all data has been read or the socket has been
            # closed. either way, reconnect and verify everything is good.
            try:
                if (
                    connection.can_read()
                    and self.cache is None
                    and not self.maint_notifications_enabled()
                ):
                    raise ConnectionError("Connection has data")
            except (ConnectionError, TimeoutError, OSError):
                connection.disconnect()
                connection.connect()
                if connection.can_read():
                    raise ConnectionError("Connection not ready")
        except BaseException:
            # release the connection back to the pool so that we don't
            # leak it
            self.release(connection)
            raise

        if is_created:
            record_connection_create_time(
                connection_pool=self,
                duration_seconds=time.monotonic() - start_time_created,
            )
        return connection

    def get_encoder(self) -> Encoder:
        "Return an encoder based on encoding settings"
        kwargs = self.connection_kwargs
        return Encoder(
            encoding=kwargs.get("encoding", "utf-8"),
            encoding_errors=kwargs.get("encoding_errors", "strict"),
            decode_responses=kwargs.get("decode_responses", False),
        )

    def make_connection(self) -> "ConnectionInterface":
        "Create a new connection"
        if self._created_connections >= self.max_connections:
            raise MaxConnectionsError("Too many connections")
        self._created_connections += 1

        kwargs = dict(self.connection_kwargs)

        if self.cache is not None:
            return CacheProxyConnection(
                self.connection_class(**kwargs), self.cache, self._lock
            )
        return self.connection_class(**kwargs)

    def release(self, connection: "Connection") -> None:
        "Releases the connection back to the pool"
        self._checkpid()
        with self._lock:
            try:
                self._in_use_connections.remove(connection)
            except KeyError:
                # Gracefully fail when a connection is returned to this pool
                # that the pool doesn't actually own
                return

            if self.owns_connection(connection):
                if connection.should_reconnect():
                    connection.disconnect()
                self._available_connections.append(connection)
                self._event_dispatcher.dispatch(
                    AfterConnectionReleasedEvent(connection)
                )
            else:
                # Pool doesn't own this connection, do not add it back
                # to the pool.
                # The created connections count should not be changed,
                # because the connection was not created by the pool.
                connection.disconnect()
                return

    def owns_connection(self, connection: "Connection") -> int:
        return connection.pid == self.pid

    def disconnect(self, inuse_connections: bool = True) -> None:
        """
        Disconnects connections in the pool

        If ``inuse_connections`` is True, disconnect connections that are
        currently in use, potentially by other threads. Otherwise only disconnect
        connections that are idle in the pool.
        """
        self._checkpid()
        with self._lock:
            if inuse_connections:
                connections = chain(
                    self._available_connections, self._in_use_connections
                )
            else:
                connections = self._available_connections

            for connection in connections:
                connection.disconnect()

    def close(self) -> None:
        """Close the pool, disconnecting all connections"""
        self.disconnect()

    def set_retry(self, retry: Retry) -> None:
        self.connection_kwargs.update({"retry": retry})
        for conn in self._available_connections:
            conn.retry = retry
        for conn in self._in_use_connections:
            conn.retry = retry

    def re_auth_callback(self, token: TokenInterface):
        with self._lock:
            for conn in self._available_connections:
                conn.retry.call_with_retry(
                    lambda: conn.send_command(
                        "AUTH", token.try_get("oid"), token.get_value()
                    ),
                    lambda error: self._mock(error),
                )
                conn.retry.call_with_retry(
                    lambda: conn.read_response(), lambda error: self._mock(error)
                )
            for conn in self._in_use_connections:
                conn.set_re_auth_token(token)

    def _get_pool_lock(self):
        return self._lock

    def _get_free_connections(self):
        with self._lock:
            return self._available_connections

    def _get_in_use_connections(self):
        with self._lock:
            return self._in_use_connections

    async def _mock(self, error: RedisError):
        """
        Dummy functions, needs to be passed as error callback to retry object.
        :param error:
        :return:
        """
        pass

    def get_connection_count(self) -> List[tuple[int, dict]]:
        from redis.observability.attributes import get_pool_name

        attributes = AttributeBuilder.build_base_attributes()
        attributes[DB_CLIENT_CONNECTION_POOL_NAME] = get_pool_name(self)
        free_connections_attributes = attributes.copy()
        in_use_connections_attributes = attributes.copy()

        free_connections_attributes[DB_CLIENT_CONNECTION_STATE] = (
            ConnectionState.IDLE.value
        )
        in_use_connections_attributes[DB_CLIENT_CONNECTION_STATE] = (
            ConnectionState.USED.value
        )

        return [
            (len(self._get_free_connections()), free_connections_attributes),
            (len(self._get_in_use_connections()), in_use_connections_attributes),
        ]


class BlockingConnectionPool(ConnectionPool):
    """
    Thread-safe blocking connection pool::

        >>> from redis.client import Redis
        >>> client = Redis(connection_pool=BlockingConnectionPool())

    It performs the same function as the default
    :py:class:`~redis.ConnectionPool` implementation, in that,
    it maintains a pool of reusable connections that can be shared by
    multiple redis clients (safely across threads if required).

    The difference is that, in the event that a client tries to get a
    connection from the pool when all of connections are in use, rather than
    raising a :py:class:`~redis.ConnectionError` (as the default
    :py:class:`~redis.ConnectionPool` implementation does), it
    makes the client wait ("blocks") for a specified number of seconds until
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
        max_connections=50,
        timeout=20,
        connection_class=Connection,
        queue_class=LifoQueue,
        **connection_kwargs,
    ):
        self.queue_class = queue_class
        self.timeout = timeout
        self._in_maintenance = False
        self._locked = False
        super().__init__(
            connection_class=connection_class,
            max_connections=max_connections,
            **connection_kwargs,
        )

    def reset(self):
        # Create and fill up a thread safe queue with ``None`` values.
        try:
            if self._in_maintenance:
                self._lock.acquire()
                self._locked = True
            self.pool = self.queue_class(self.max_connections)
            while True:
                try:
                    self.pool.put_nowait(None)
                except Full:
                    break

            # Keep a list of actual connection instances so that we can
            # disconnect them later.
            self._connections = []
        finally:
            if self._locked:
                try:
                    self._lock.release()
                except Exception:
                    pass
                self._locked = False

        # this must be the last operation in this method. while reset() is
        # called when holding _fork_lock, other threads in this process
        # can call _checkpid() which compares self.pid and os.getpid() without
        # holding any lock (for performance reasons). keeping this assignment
        # as the last operation ensures that those other threads will also
        # notice a pid difference and block waiting for the first thread to
        # release _fork_lock. when each of these threads eventually acquire
        # _fork_lock, they will notice that another thread already called
        # reset() and they will immediately release _fork_lock and continue on.
        self.pid = os.getpid()

    def make_connection(self):
        "Make a fresh connection."
        try:
            if self._in_maintenance:
                self._lock.acquire()
                self._locked = True

            if self.cache is not None:
                connection = CacheProxyConnection(
                    self.connection_class(**self.connection_kwargs),
                    self.cache,
                    self._lock,
                )
            else:
                connection = self.connection_class(**self.connection_kwargs)
            self._connections.append(connection)
            return connection
        finally:
            if self._locked:
                try:
                    self._lock.release()
                except Exception:
                    pass
                self._locked = False

    @deprecated_args(
        args_to_warn=["*"],
        reason="Use get_connection() without args instead",
        version="5.3.0",
    )
    def get_connection(self, command_name=None, *keys, **options):
        """
        Get a connection, blocking for ``self.timeout`` until a connection
        is available from the pool.

        If the connection returned is ``None`` then creates a new connection.
        Because we use a last-in first-out queue, the existing connections
        (having been returned to the pool after the initial ``None`` values
        were added) will be returned before ``None`` values. This means we only
        create new connections when we need to, i.e.: the actual number of
        connections will only increase in response to demand.
        """
        start_time_acquired = time.monotonic()
        # Make sure we haven't changed process.
        self._checkpid()
        is_created = False

        # Try and get a connection from the pool. If one isn't available within
        # self.timeout then raise a ``ConnectionError``.
        connection = None
        try:
            if self._in_maintenance:
                self._lock.acquire()
                self._locked = True
            try:
                connection = self.pool.get(block=True, timeout=self.timeout)
            except Empty:
                # Note that this is not caught by the redis client and will be
                # raised unless handled by application code. If you want never to
                raise ConnectionError("No connection available.")

            # If the ``connection`` is actually ``None`` then that's a cue to make
            # a new connection to add to the pool.
            if connection is None:
                # Start timing for observability
                start_time_created = time.monotonic()
                connection = self.make_connection()
                is_created = True
        finally:
            if self._locked:
                try:
                    self._lock.release()
                except Exception:
                    pass
                self._locked = False

        try:
            # ensure this connection is connected to Redis
            connection.connect()
            # connections that the pool provides should be ready to send
            # a command. if not, the connection was either returned to the
            # pool before all data has been read or the socket has been
            # closed. either way, reconnect and verify everything is good.
            try:
                if connection.can_read():
                    raise ConnectionError("Connection has data")
            except (ConnectionError, TimeoutError, OSError):
                connection.disconnect()
                connection.connect()
                if connection.can_read():
                    raise ConnectionError("Connection not ready")
        except BaseException:
            # release the connection back to the pool so that we don't leak it
            self.release(connection)
            raise

        if is_created:
            record_connection_create_time(
                connection_pool=self,
                duration_seconds=time.monotonic() - start_time_created,
            )

        record_connection_wait_time(
            pool_name=get_pool_name(self),
            duration_seconds=time.monotonic() - start_time_acquired,
        )

        return connection

    def release(self, connection):
        "Releases the connection back to the pool."
        # Make sure we haven't changed process.
        self._checkpid()

        try:
            if self._in_maintenance:
                self._lock.acquire()
                self._locked = True
            if not self.owns_connection(connection):
                # pool doesn't own this connection. do not add it back
                # to the pool. instead add a None value which is a placeholder
                # that will cause the pool to recreate the connection if
                # its needed.
                connection.disconnect()
                self.pool.put_nowait(None)
                return
            if connection.should_reconnect():
                connection.disconnect()
            # Put the connection back into the pool.
            try:
                self.pool.put_nowait(connection)
            except Full:
                # perhaps the pool has been reset() after a fork? regardless,
                # we don't want this connection
                pass
        finally:
            if self._locked:
                try:
                    self._lock.release()
                except Exception:
                    pass
                self._locked = False

    def disconnect(self, inuse_connections: bool = True):
        "Disconnects either all connections in the pool or just the free connections."
        self._checkpid()
        try:
            if self._in_maintenance:
                self._lock.acquire()
                self._locked = True
            if inuse_connections:
                connections = self._connections
            else:
                connections = self._get_free_connections()
            for connection in connections:
                connection.disconnect()
        finally:
            if self._locked:
                try:
                    self._lock.release()
                except Exception:
                    pass
                self._locked = False

    def _get_free_connections(self):
        with self._lock:
            return {conn for conn in self.pool.queue if conn}

    def _get_in_use_connections(self):
        with self._lock:
            # free connections
            connections_in_queue = {conn for conn in self.pool.queue if conn}
            # in self._connections we keep all created connections
            # so the ones that are not in the queue are the in use ones
            return {
                conn for conn in self._connections if conn not in connections_in_queue
            }

    def set_in_maintenance(self, in_maintenance: bool):
        """
        Sets a flag that this Blocking ConnectionPool is in maintenance mode.

        This is used to prevent new connections from being created while we are in maintenance mode.
        The pool will be in maintenance mode only when we are processing a MOVING notification.
        """
        self._in_maintenance = in_maintenance
