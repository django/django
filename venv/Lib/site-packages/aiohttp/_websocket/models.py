"""Models for WebSocket protocol versions 13 and 8."""

import json
from enum import IntEnum
from typing import Any, Callable, Final, NamedTuple, Optional, cast

WS_DEFLATE_TRAILING: Final[bytes] = bytes([0x00, 0x00, 0xFF, 0xFF])


class WSCloseCode(IntEnum):
    OK = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    ABNORMAL_CLOSURE = 1006
    INVALID_TEXT = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014


class WSMsgType(IntEnum):
    # websocket spec types
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    PING = 0x9
    PONG = 0xA
    CLOSE = 0x8

    # aiohttp specific types
    CLOSING = 0x100
    CLOSED = 0x101
    ERROR = 0x102

    text = TEXT
    binary = BINARY
    ping = PING
    pong = PONG
    close = CLOSE
    closing = CLOSING
    closed = CLOSED
    error = ERROR


class WSMessage(NamedTuple):
    type: WSMsgType
    # To type correctly, this would need some kind of tagged union for each type.
    data: Any
    extra: Optional[str]

    def json(self, *, loads: Callable[[Any], Any] = json.loads) -> Any:
        """Return parsed JSON data.

        .. versionadded:: 0.22
        """
        return loads(self.data)


# Constructing the tuple directly to avoid the overhead of
# the lambda and arg processing since NamedTuples are constructed
# with a run time built lambda
# https://github.com/python/cpython/blob/d83fcf8371f2f33c7797bc8f5423a8bca8c46e5c/Lib/collections/__init__.py#L441
WS_CLOSED_MESSAGE = tuple.__new__(WSMessage, (WSMsgType.CLOSED, None, None))
WS_CLOSING_MESSAGE = tuple.__new__(WSMessage, (WSMsgType.CLOSING, None, None))


class WebSocketError(Exception):
    """WebSocket protocol parser error."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        super().__init__(code, message)

    def __str__(self) -> str:
        return cast(str, self.args[1])


class WSHandshakeError(Exception):
    """WebSocket protocol handshake error."""
