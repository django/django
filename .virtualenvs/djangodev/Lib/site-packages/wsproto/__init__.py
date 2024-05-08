"""
wsproto
~~~~~~~

A WebSocket implementation.
"""
from typing import Generator, Optional, Union

from .connection import Connection, ConnectionState, ConnectionType
from .events import Event
from .handshake import H11Handshake
from .typing import Headers

__version__ = "1.2.0"


class WSConnection:
    """
    Represents the local end of a WebSocket connection to a remote peer.
    """

    def __init__(self, connection_type: ConnectionType) -> None:
        """
        Constructor

        :param wsproto.connection.ConnectionType connection_type: Controls
            whether the library behaves as a client or as a server.
        """
        self.client = connection_type is ConnectionType.CLIENT
        self.handshake = H11Handshake(connection_type)
        self.connection: Optional[Connection] = None

    @property
    def state(self) -> ConnectionState:
        """
        :returns: Connection state
        :rtype: wsproto.connection.ConnectionState
        """
        if self.connection is None:
            return self.handshake.state
        return self.connection.state

    def initiate_upgrade_connection(
        self, headers: Headers, path: Union[bytes, str]
    ) -> None:
        self.handshake.initiate_upgrade_connection(headers, path)

    def send(self, event: Event) -> bytes:
        """
        Generate network data for the specified event.

        When you want to communicate with a WebSocket peer, you should construct
        an event and pass it to this method. This method will return the bytes
        that you should send to the peer.

        :param wsproto.events.Event event: The event to generate data for
        :returns bytes: The data to send to the peer
        """
        data = b""
        if self.connection is None:
            data += self.handshake.send(event)
            self.connection = self.handshake.connection
        else:
            data += self.connection.send(event)
        return data

    def receive_data(self, data: Optional[bytes]) -> None:
        """
        Feed network data into the connection instance.

        After calling this method, you should call :meth:`events` to see if the
        received data triggered any new events.

        :param bytes data: Data received from remote peer
        """
        if self.connection is None:
            self.handshake.receive_data(data)
            self.connection = self.handshake.connection
        else:
            self.connection.receive_data(data)

    def events(self) -> Generator[Event, None, None]:
        """
        A generator that yields pending events.

        Each event is an instance of a subclass of
        :class:`wsproto.events.Event`.
        """
        yield from self.handshake.events()
        if self.connection is not None:
            yield from self.connection.events()


__all__ = ("ConnectionType", "WSConnection")
