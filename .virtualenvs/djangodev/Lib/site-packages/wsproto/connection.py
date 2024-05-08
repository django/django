"""
wsproto/connection
~~~~~~~~~~~~~~~~~~

An implementation of a WebSocket connection.
"""

from collections import deque
from enum import Enum
from typing import Deque, Generator, List, Optional

from .events import (
    BytesMessage,
    CloseConnection,
    Event,
    Message,
    Ping,
    Pong,
    TextMessage,
)
from .extensions import Extension
from .frame_protocol import CloseReason, FrameProtocol, Opcode, ParseFailed
from .utilities import LocalProtocolError


class ConnectionState(Enum):
    """
    RFC 6455, Section 4 - Opening Handshake
    """

    #: The opening handshake is in progress.
    CONNECTING = 0
    #: The opening handshake is complete.
    OPEN = 1
    #: The remote WebSocket has initiated a connection close.
    REMOTE_CLOSING = 2
    #: The local WebSocket (i.e. this instance) has initiated a connection close.
    LOCAL_CLOSING = 3
    #: The closing handshake has completed.
    CLOSED = 4
    #: The connection was rejected during the opening handshake.
    REJECTING = 5


class ConnectionType(Enum):
    """An enumeration of connection types."""

    #: This connection will act as client and talk to a remote server
    CLIENT = 1

    #: This connection will as as server and waits for client connections
    SERVER = 2


CLIENT = ConnectionType.CLIENT
SERVER = ConnectionType.SERVER


class Connection:
    """
    A low-level WebSocket connection object.

    This wraps two other protocol objects, an HTTP/1.1 protocol object used
    to do the initial HTTP upgrade handshake and a WebSocket frame protocol
    object used to exchange messages and other control frames.

    :param conn_type: Whether this object is on the client- or server-side of
        a connection. To initialise as a client pass ``CLIENT`` otherwise
        pass ``SERVER``.
    :type conn_type: ``ConnectionType``
    """

    def __init__(
        self,
        connection_type: ConnectionType,
        extensions: Optional[List[Extension]] = None,
        trailing_data: bytes = b"",
    ) -> None:
        self.client = connection_type is ConnectionType.CLIENT
        self._events: Deque[Event] = deque()
        self._proto = FrameProtocol(self.client, extensions or [])
        self._state = ConnectionState.OPEN
        self.receive_data(trailing_data)

    @property
    def state(self) -> ConnectionState:
        return self._state

    def send(self, event: Event) -> bytes:
        data = b""
        if isinstance(event, Message) and self.state == ConnectionState.OPEN:
            data += self._proto.send_data(event.data, event.message_finished)
        elif isinstance(event, Ping) and self.state == ConnectionState.OPEN:
            data += self._proto.ping(event.payload)
        elif isinstance(event, Pong) and self.state == ConnectionState.OPEN:
            data += self._proto.pong(event.payload)
        elif isinstance(event, CloseConnection) and self.state in {
            ConnectionState.OPEN,
            ConnectionState.REMOTE_CLOSING,
        }:
            data += self._proto.close(event.code, event.reason)
            if self.state == ConnectionState.REMOTE_CLOSING:
                self._state = ConnectionState.CLOSED
            else:
                self._state = ConnectionState.LOCAL_CLOSING
        else:
            raise LocalProtocolError(
                f"Event {event} cannot be sent in state {self.state}."
            )
        return data

    def receive_data(self, data: Optional[bytes]) -> None:
        """
        Pass some received data to the connection for handling.

        A list of events that the remote peer triggered by sending this data can
        be retrieved with :meth:`~wsproto.connection.Connection.events`.

        :param data: The data received from the remote peer on the network.
        :type data: ``bytes``
        """

        if data is None:
            # "If _The WebSocket Connection is Closed_ and no Close control
            # frame was received by the endpoint (such as could occur if the
            # underlying transport connection is lost), _The WebSocket
            # Connection Close Code_ is considered to be 1006."
            self._events.append(CloseConnection(code=CloseReason.ABNORMAL_CLOSURE))
            self._state = ConnectionState.CLOSED
            return

        if self.state in (ConnectionState.OPEN, ConnectionState.LOCAL_CLOSING):
            self._proto.receive_bytes(data)
        elif self.state is ConnectionState.CLOSED:
            raise LocalProtocolError("Connection already closed.")
        else:
            pass  # pragma: no cover

    def events(self) -> Generator[Event, None, None]:
        """
        Return a generator that provides any events that have been generated
        by protocol activity.

        :returns: generator of :class:`Event <wsproto.events.Event>` subclasses
        """
        while self._events:
            yield self._events.popleft()

        try:
            for frame in self._proto.received_frames():
                if frame.opcode is Opcode.PING:
                    assert frame.frame_finished and frame.message_finished
                    assert isinstance(frame.payload, (bytes, bytearray))
                    yield Ping(payload=frame.payload)

                elif frame.opcode is Opcode.PONG:
                    assert frame.frame_finished and frame.message_finished
                    assert isinstance(frame.payload, (bytes, bytearray))
                    yield Pong(payload=frame.payload)

                elif frame.opcode is Opcode.CLOSE:
                    assert isinstance(frame.payload, tuple)
                    code, reason = frame.payload
                    if self.state is ConnectionState.LOCAL_CLOSING:
                        self._state = ConnectionState.CLOSED
                    else:
                        self._state = ConnectionState.REMOTE_CLOSING
                    yield CloseConnection(code=code, reason=reason)

                elif frame.opcode is Opcode.TEXT:
                    assert isinstance(frame.payload, str)
                    yield TextMessage(
                        data=frame.payload,
                        frame_finished=frame.frame_finished,
                        message_finished=frame.message_finished,
                    )

                elif frame.opcode is Opcode.BINARY:
                    assert isinstance(frame.payload, (bytes, bytearray))
                    yield BytesMessage(
                        data=frame.payload,
                        frame_finished=frame.frame_finished,
                        message_finished=frame.message_finished,
                    )

                else:
                    pass  # pragma: no cover
        except ParseFailed as exc:
            yield CloseConnection(code=exc.code, reason=str(exc))
