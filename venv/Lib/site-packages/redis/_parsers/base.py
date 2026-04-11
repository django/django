import logging
import sys
from abc import ABC
from asyncio import IncompleteReadError, StreamReader, TimeoutError
from typing import Awaitable, Callable, List, Optional, Protocol, Union

from redis.maint_notifications import (
    MaintenanceNotification,
    NodeFailedOverNotification,
    NodeFailingOverNotification,
    NodeMigratedNotification,
    NodeMigratingNotification,
    NodeMovingNotification,
    OSSNodeMigratedNotification,
    OSSNodeMigratingNotification,
)
from redis.utils import safe_str

if sys.version_info.major >= 3 and sys.version_info.minor >= 11:
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout

from ..exceptions import (
    AskError,
    AuthenticationError,
    AuthenticationWrongNumberOfArgsError,
    BusyLoadingError,
    ClusterCrossSlotError,
    ClusterDownError,
    ConnectionError,
    ExecAbortError,
    ExternalAuthProviderError,
    MasterDownError,
    ModuleError,
    MovedError,
    NoPermissionError,
    NoScriptError,
    OutOfMemoryError,
    ReadOnlyError,
    ResponseError,
    TryAgainError,
)
from ..typing import EncodableT
from .encoders import Encoder
from .socket import SERVER_CLOSED_CONNECTION_ERROR, SocketBuffer

MODULE_LOAD_ERROR = "Error loading the extension. Please check the server logs."
NO_SUCH_MODULE_ERROR = "Error unloading module: no such module with that name"
MODULE_UNLOAD_NOT_POSSIBLE_ERROR = "Error unloading module: operation not possible."
MODULE_EXPORTS_DATA_TYPES_ERROR = (
    "Error unloading module: the module "
    "exports one or more module-side data "
    "types, can't unload"
)
# user send an AUTH cmd to a server without authorization configured
NO_AUTH_SET_ERROR = {
    # Redis >= 6.0
    "AUTH <password> called without any password "
    "configured for the default user. Are you sure "
    "your configuration is correct?": AuthenticationError,
    # Redis < 6.0
    "Client sent AUTH, but no password is set": AuthenticationError,
}

EXTERNAL_AUTH_PROVIDER_ERROR = {
    "problem with LDAP service": ExternalAuthProviderError,
}

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    EXCEPTION_CLASSES = {
        "ERR": {
            "max number of clients reached": ConnectionError,
            "invalid password": AuthenticationError,
            # some Redis server versions report invalid command syntax
            # in lowercase
            "wrong number of arguments "
            "for 'auth' command": AuthenticationWrongNumberOfArgsError,
            # some Redis server versions report invalid command syntax
            # in uppercase
            "wrong number of arguments "
            "for 'AUTH' command": AuthenticationWrongNumberOfArgsError,
            MODULE_LOAD_ERROR: ModuleError,
            MODULE_EXPORTS_DATA_TYPES_ERROR: ModuleError,
            NO_SUCH_MODULE_ERROR: ModuleError,
            MODULE_UNLOAD_NOT_POSSIBLE_ERROR: ModuleError,
            **NO_AUTH_SET_ERROR,
            **EXTERNAL_AUTH_PROVIDER_ERROR,
        },
        "OOM": OutOfMemoryError,
        "WRONGPASS": AuthenticationError,
        "EXECABORT": ExecAbortError,
        "LOADING": BusyLoadingError,
        "NOSCRIPT": NoScriptError,
        "READONLY": ReadOnlyError,
        "NOAUTH": AuthenticationError,
        "NOPERM": NoPermissionError,
        "ASK": AskError,
        "TRYAGAIN": TryAgainError,
        "MOVED": MovedError,
        "CLUSTERDOWN": ClusterDownError,
        "CROSSSLOT": ClusterCrossSlotError,
        "MASTERDOWN": MasterDownError,
    }

    @classmethod
    def parse_error(cls, response):
        "Parse an error response"
        error_code = response.split(" ")[0]
        if error_code in cls.EXCEPTION_CLASSES:
            response = response[len(error_code) + 1 :]
            exception_class = cls.EXCEPTION_CLASSES[error_code]
            if isinstance(exception_class, dict):
                exception_class = exception_class.get(response, ResponseError)
            return exception_class(response, status_code=error_code)
        return ResponseError(response)

    def on_disconnect(self):
        raise NotImplementedError()

    def on_connect(self, connection):
        raise NotImplementedError()


class _RESPBase(BaseParser):
    """Base class for sync-based resp parsing"""

    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size
        self.encoder = None
        self._sock = None
        self._buffer = None

    def __del__(self):
        try:
            self.on_disconnect()
        except Exception:
            pass

    def on_connect(self, connection):
        "Called when the socket connects"
        self._sock = connection._sock
        self._buffer = SocketBuffer(
            self._sock, self.socket_read_size, connection.socket_timeout
        )
        self.encoder = connection.encoder

    def on_disconnect(self):
        "Called when the socket disconnects"
        self._sock = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None
        self.encoder = None

    def can_read(self, timeout):
        return self._buffer and self._buffer.can_read(timeout)


class AsyncBaseParser(BaseParser):
    """Base parsing class for the python-backed async parser"""

    __slots__ = "_stream", "_read_size"

    def __init__(self, socket_read_size: int):
        self._stream: Optional[StreamReader] = None
        self._read_size = socket_read_size

    async def can_read_destructive(self) -> bool:
        raise NotImplementedError()

    async def read_response(
        self, disable_decoding: bool = False
    ) -> Union[EncodableT, ResponseError, None, List[EncodableT]]:
        raise NotImplementedError()


class MaintenanceNotificationsParser:
    """Protocol defining maintenance push notification parsing functionality"""

    @staticmethod
    def parse_oss_maintenance_start_msg(response):
        # Expected message format is:
        # SMIGRATING <seq_number> <slot, range1-range2,...>
        id = response[1]
        slots = safe_str(response[2])
        return OSSNodeMigratingNotification(id, slots)

    @staticmethod
    def parse_oss_maintenance_completed_msg(response):
        # Expected message format is:
        # SMIGRATED <seq_number> [[<src_host:port> <dest_host:port> <slot_range>], ...]
        id = response[1]
        nodes_to_slots_mapping_data = response[2]
        # Build the nodes_to_slots_mapping dict structure:
        # {
        #     "src_host:port": [
        #         {"dest_host:port": "slot_range"},
        #         ...
        #     ],
        #     ...
        # }
        nodes_to_slots_mapping = {}
        for src_node, dest_node, slots in nodes_to_slots_mapping_data:
            src_node_str = safe_str(src_node)
            dest_node_str = safe_str(dest_node)
            slots_str = safe_str(slots)

            if src_node_str not in nodes_to_slots_mapping:
                nodes_to_slots_mapping[src_node_str] = []
            nodes_to_slots_mapping[src_node_str].append({dest_node_str: slots_str})

        return OSSNodeMigratedNotification(id, nodes_to_slots_mapping)

    @staticmethod
    def parse_maintenance_start_msg(response, notification_type):
        # Expected message format is: <notification_type> <seq_number> <time>
        # Examples:
        # MIGRATING 1 10
        # FAILING_OVER 2 20
        id = response[1]
        ttl = response[2]
        return notification_type(id, ttl)

    @staticmethod
    def parse_maintenance_completed_msg(response, notification_type):
        # Expected message format is: <notification_type> <seq_number>
        # Examples:
        # MIGRATED 1
        # FAILED_OVER 2
        id = response[1]
        return notification_type(id)

    @staticmethod
    def parse_moving_msg(response):
        # Expected message format is: MOVING <seq_number> <time> <endpoint>
        id = response[1]
        ttl = response[2]
        if response[3] is None:
            host, port = None, None
        else:
            value = safe_str(response[3])
            host, port = value.split(":")
            port = int(port) if port is not None else None

        return NodeMovingNotification(id, host, port, ttl)


_INVALIDATION_MESSAGE = "invalidate"
_MOVING_MESSAGE = "MOVING"
_MIGRATING_MESSAGE = "MIGRATING"
_MIGRATED_MESSAGE = "MIGRATED"
_FAILING_OVER_MESSAGE = "FAILING_OVER"
_FAILED_OVER_MESSAGE = "FAILED_OVER"
_SMIGRATING_MESSAGE = "SMIGRATING"
_SMIGRATED_MESSAGE = "SMIGRATED"

_MAINTENANCE_MESSAGES = (
    _MIGRATING_MESSAGE,
    _MIGRATED_MESSAGE,
    _FAILING_OVER_MESSAGE,
    _FAILED_OVER_MESSAGE,
    _SMIGRATING_MESSAGE,
)

MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING: dict[
    str, tuple[type[MaintenanceNotification], Callable]
] = {
    _MIGRATING_MESSAGE: (
        NodeMigratingNotification,
        MaintenanceNotificationsParser.parse_maintenance_start_msg,
    ),
    _MIGRATED_MESSAGE: (
        NodeMigratedNotification,
        MaintenanceNotificationsParser.parse_maintenance_completed_msg,
    ),
    _FAILING_OVER_MESSAGE: (
        NodeFailingOverNotification,
        MaintenanceNotificationsParser.parse_maintenance_start_msg,
    ),
    _FAILED_OVER_MESSAGE: (
        NodeFailedOverNotification,
        MaintenanceNotificationsParser.parse_maintenance_completed_msg,
    ),
    _MOVING_MESSAGE: (
        NodeMovingNotification,
        MaintenanceNotificationsParser.parse_moving_msg,
    ),
    _SMIGRATING_MESSAGE: (
        OSSNodeMigratingNotification,
        MaintenanceNotificationsParser.parse_oss_maintenance_start_msg,
    ),
    _SMIGRATED_MESSAGE: (
        OSSNodeMigratedNotification,
        MaintenanceNotificationsParser.parse_oss_maintenance_completed_msg,
    ),
}


class PushNotificationsParser(Protocol):
    """Protocol defining RESP3-specific parsing functionality"""

    pubsub_push_handler_func: Callable
    invalidation_push_handler_func: Optional[Callable] = None
    node_moving_push_handler_func: Optional[Callable] = None
    maintenance_push_handler_func: Optional[Callable] = None
    oss_cluster_maint_push_handler_func: Optional[Callable] = None

    def handle_pubsub_push_response(self, response):
        """Handle pubsub push responses"""
        raise NotImplementedError()

    def handle_push_response(self, response, **kwargs):
        msg_type = response[0]
        if isinstance(msg_type, bytes):
            msg_type = msg_type.decode()

        if msg_type not in (
            _INVALIDATION_MESSAGE,
            *_MAINTENANCE_MESSAGES,
            _MOVING_MESSAGE,
            _SMIGRATED_MESSAGE,
        ):
            return self.pubsub_push_handler_func(response)

        try:
            if (
                msg_type == _INVALIDATION_MESSAGE
                and self.invalidation_push_handler_func
            ):
                return self.invalidation_push_handler_func(response)

            if msg_type == _MOVING_MESSAGE and self.node_moving_push_handler_func:
                parser_function = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                    msg_type
                ][1]

                notification = parser_function(response)
                return self.node_moving_push_handler_func(notification)

            if msg_type in _MAINTENANCE_MESSAGES and self.maintenance_push_handler_func:
                parser_function = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                    msg_type
                ][1]
                if msg_type == _SMIGRATING_MESSAGE:
                    notification = parser_function(response)
                else:
                    notification_type = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                        msg_type
                    ][0]
                    notification = parser_function(response, notification_type)

                if notification is not None:
                    return self.maintenance_push_handler_func(notification)
            if msg_type == _SMIGRATED_MESSAGE and (
                self.oss_cluster_maint_push_handler_func
                or self.maintenance_push_handler_func
            ):
                parser_function = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                    msg_type
                ][1]
                notification = parser_function(response)

                if notification is not None:
                    if self.maintenance_push_handler_func:
                        self.maintenance_push_handler_func(notification)
                    if self.oss_cluster_maint_push_handler_func:
                        self.oss_cluster_maint_push_handler_func(notification)
        except Exception as e:
            logger.error(
                "Error handling {} message ({}): {}".format(msg_type, response, e)
            )

        return None

    def set_pubsub_push_handler(self, pubsub_push_handler_func):
        self.pubsub_push_handler_func = pubsub_push_handler_func

    def set_invalidation_push_handler(self, invalidation_push_handler_func):
        self.invalidation_push_handler_func = invalidation_push_handler_func

    def set_node_moving_push_handler(self, node_moving_push_handler_func):
        self.node_moving_push_handler_func = node_moving_push_handler_func

    def set_maintenance_push_handler(self, maintenance_push_handler_func):
        self.maintenance_push_handler_func = maintenance_push_handler_func

    def set_oss_cluster_maint_push_handler(self, oss_cluster_maint_push_handler_func):
        self.oss_cluster_maint_push_handler_func = oss_cluster_maint_push_handler_func


class AsyncPushNotificationsParser(Protocol):
    """Protocol defining async RESP3-specific parsing functionality"""

    pubsub_push_handler_func: Callable
    invalidation_push_handler_func: Optional[Callable] = None
    node_moving_push_handler_func: Optional[Callable[..., Awaitable[None]]] = None
    maintenance_push_handler_func: Optional[Callable[..., Awaitable[None]]] = None
    oss_cluster_maint_push_handler_func: Optional[Callable[..., Awaitable[None]]] = None

    async def handle_pubsub_push_response(self, response):
        """Handle pubsub push responses asynchronously"""
        raise NotImplementedError()

    async def handle_push_response(self, response, **kwargs):
        """Handle push responses asynchronously"""

        msg_type = response[0]
        if isinstance(msg_type, bytes):
            msg_type = msg_type.decode()

        if msg_type not in (
            _INVALIDATION_MESSAGE,
            *_MAINTENANCE_MESSAGES,
            _MOVING_MESSAGE,
            _SMIGRATED_MESSAGE,
        ):
            return await self.pubsub_push_handler_func(response)

        try:
            if (
                msg_type == _INVALIDATION_MESSAGE
                and self.invalidation_push_handler_func
            ):
                return await self.invalidation_push_handler_func(response)

            if isinstance(msg_type, bytes):
                msg_type = msg_type.decode()

            if msg_type == _MOVING_MESSAGE and self.node_moving_push_handler_func:
                parser_function = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                    msg_type
                ][1]
                notification = parser_function(response)
                return await self.node_moving_push_handler_func(notification)

            if msg_type in _MAINTENANCE_MESSAGES and self.maintenance_push_handler_func:
                parser_function = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                    msg_type
                ][1]
                if msg_type == _SMIGRATING_MESSAGE:
                    notification = parser_function(response)
                else:
                    notification_type = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                        msg_type
                    ][0]
                    notification = parser_function(response, notification_type)

                if notification is not None:
                    return await self.maintenance_push_handler_func(notification)
            if (
                msg_type == _SMIGRATED_MESSAGE
                and self.oss_cluster_maint_push_handler_func
            ):
                parser_function = MSG_TYPE_TO_MAINT_NOTIFICATION_PARSER_MAPPING[
                    msg_type
                ][1]
                notification = parser_function(response)
                if notification is not None:
                    return await self.oss_cluster_maint_push_handler_func(notification)
        except Exception as e:
            logger.error(
                "Error handling {} message ({}): {}".format(msg_type, response, e)
            )

        return None

    def set_pubsub_push_handler(self, pubsub_push_handler_func):
        """Set the pubsub push handler function"""
        self.pubsub_push_handler_func = pubsub_push_handler_func

    def set_invalidation_push_handler(self, invalidation_push_handler_func):
        """Set the invalidation push handler function"""
        self.invalidation_push_handler_func = invalidation_push_handler_func

    def set_node_moving_push_handler(self, node_moving_push_handler_func):
        self.node_moving_push_handler_func = node_moving_push_handler_func

    def set_maintenance_push_handler(self, maintenance_push_handler_func):
        self.maintenance_push_handler_func = maintenance_push_handler_func

    def set_oss_cluster_maint_push_handler(self, oss_cluster_maint_push_handler_func):
        self.oss_cluster_maint_push_handler_func = oss_cluster_maint_push_handler_func


class _AsyncRESPBase(AsyncBaseParser):
    """Base class for async resp parsing"""

    __slots__ = AsyncBaseParser.__slots__ + ("encoder", "_buffer", "_pos", "_chunks")

    def __init__(self, socket_read_size: int):
        super().__init__(socket_read_size)
        self.encoder: Optional[Encoder] = None
        self._buffer = b""
        self._chunks = []
        self._pos = 0

    def _clear(self):
        self._buffer = b""
        self._chunks.clear()

    def on_connect(self, connection):
        """Called when the stream connects"""
        self._stream = connection._reader
        if self._stream is None:
            raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
        self.encoder = connection.encoder
        self._clear()
        self._connected = True

    def on_disconnect(self):
        """Called when the stream disconnects"""
        self._connected = False

    async def can_read_destructive(self) -> bool:
        if not self._connected:
            raise OSError("Buffer is closed.")
        if self._buffer:
            return True
        try:
            async with async_timeout(0):
                return self._stream.at_eof()
        except TimeoutError:
            return False

    async def _read(self, length: int) -> bytes:
        """
        Read `length` bytes of data.  These are assumed to be followed
        by a '\r\n' terminator which is subsequently discarded.
        """
        want = length + 2
        end = self._pos + want
        if len(self._buffer) >= end:
            result = self._buffer[self._pos : end - 2]
        else:
            tail = self._buffer[self._pos :]
            try:
                data = await self._stream.readexactly(want - len(tail))
            except IncompleteReadError as error:
                raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR) from error
            result = (tail + data)[:-2]
            self._chunks.append(data)
        self._pos += want
        return result

    async def _readline(self) -> bytes:
        """
        read an unknown number of bytes up to the next '\r\n'
        line separator, which is discarded.
        """
        found = self._buffer.find(b"\r\n", self._pos)
        if found >= 0:
            result = self._buffer[self._pos : found]
        else:
            tail = self._buffer[self._pos :]
            data = await self._stream.readline()
            if not data.endswith(b"\r\n"):
                raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
            result = (tail + data)[:-2]
            self._chunks.append(data)
        self._pos += len(result) + 2
        return result
