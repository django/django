"""WebSocket protocol versions 13 and 8."""

from ._websocket.helpers import WS_KEY, ws_ext_gen, ws_ext_parse
from ._websocket.models import (
    WS_CLOSED_MESSAGE,
    WS_CLOSING_MESSAGE,
    WebSocketError,
    WSCloseCode,
    WSHandshakeError,
    WSMessage,
    WSMsgType,
)
from ._websocket.reader import WebSocketReader
from ._websocket.writer import WebSocketWriter

# Messages that the WebSocketResponse.receive needs to handle internally
_INTERNAL_RECEIVE_TYPES = frozenset(
    (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.PING, WSMsgType.PONG)
)


__all__ = (
    "WS_CLOSED_MESSAGE",
    "WS_CLOSING_MESSAGE",
    "WS_KEY",
    "WebSocketReader",
    "WebSocketWriter",
    "WSMessage",
    "WebSocketError",
    "WSMsgType",
    "WSCloseCode",
    "ws_ext_gen",
    "ws_ext_parse",
    "WSHandshakeError",
    "WSMessage",
)
