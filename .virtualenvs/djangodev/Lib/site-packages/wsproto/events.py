"""
wsproto/events
~~~~~~~~~~~~~~

Events that result from processing data on a WebSocket connection.
"""
from abc import ABC
from dataclasses import dataclass, field
from typing import Generic, List, Optional, Sequence, TypeVar, Union

from .extensions import Extension
from .typing import Headers


class Event(ABC):
    """
    Base class for wsproto events.
    """

    pass  # noqa


@dataclass(frozen=True)
class Request(Event):
    """The beginning of a Websocket connection, the HTTP Upgrade request

    This event is fired when a SERVER connection receives a WebSocket
    handshake request (HTTP with upgrade header).

    Fields:

    .. attribute:: host

       (Required) The hostname, or host header value.

    .. attribute:: target

       (Required) The request target (path and query string)

    .. attribute:: extensions

       The proposed extensions.

    .. attribute:: extra_headers

       The additional request headers, excluding extensions, host, subprotocols,
       and version headers.

    .. attribute:: subprotocols

       A list of the subprotocols proposed in the request, as a list
       of strings.
    """

    host: str
    target: str
    extensions: Union[Sequence[Extension], Sequence[str]] = field(  # type: ignore[assignment]
        default_factory=list
    )
    extra_headers: Headers = field(default_factory=list)
    subprotocols: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AcceptConnection(Event):
    """The acceptance of a Websocket upgrade request.

    This event is fired when a CLIENT receives an acceptance response
    from a server. It is also used to accept an upgrade request when
    acting as a SERVER.

    Fields:

    .. attribute:: extra_headers

       Any additional (non websocket related) headers present in the
       acceptance response.

    .. attribute:: subprotocol

       The accepted subprotocol to use.

    """

    subprotocol: Optional[str] = None
    extensions: List[Extension] = field(default_factory=list)
    extra_headers: Headers = field(default_factory=list)


@dataclass(frozen=True)
class RejectConnection(Event):
    """The rejection of a Websocket upgrade request, the HTTP response.

    The ``RejectConnection`` event sends the appropriate HTTP headers to
    communicate to the peer that the handshake has been rejected. You may also
    send an HTTP body by setting the ``has_body`` attribute to ``True`` and then
    sending one or more :class:`RejectData` events after this one. When sending
    a response body, the caller should set the ``Content-Length``,
    ``Content-Type``, and/or ``Transfer-Encoding`` headers as appropriate.

    When receiving a ``RejectConnection`` event, the ``has_body`` attribute will
    in almost all cases be ``True`` (even if the server set it to ``False``) and
    will be followed by at least one ``RejectData`` events, even though the data
    itself might be just ``b""``. (The only scenario in which the caller
    receives a ``RejectConnection`` with ``has_body == False`` is if the peer
    violates sends an informational status code (1xx) other than 101.)

    The ``has_body`` attribute should only be used when receiving the event. (It
    has ) is False the headers must include a
    content-length or transfer encoding.

    Fields:

    .. attribute:: headers (Headers)

       The headers to send with the response.

    .. attribute:: has_body

       This defaults to False, but set to True if there is a body. See
       also :class:`~RejectData`.

    .. attribute:: status_code

       The response status code.

    """

    status_code: int = 400
    headers: Headers = field(default_factory=list)
    has_body: bool = False


@dataclass(frozen=True)
class RejectData(Event):
    """The rejection HTTP response body.

    The caller may send multiple ``RejectData`` events. The final event should
    have the ``body_finished`` attribute set to ``True``.

    Fields:

    .. attribute:: body_finished

       True if this is the final chunk of the body data.

    .. attribute:: data (bytes)

       (Required) The raw body data.

    """

    data: bytes
    body_finished: bool = True


@dataclass(frozen=True)
class CloseConnection(Event):

    """The end of a Websocket connection, represents a closure frame.

    **wsproto does not automatically send a response to a close event.** To
    comply with the RFC you MUST send a close event back to the remote WebSocket
    if you have not already sent one. The :meth:`response` method provides a
    suitable event for this purpose, and you should check if a response needs
    to be sent by checking :func:`wsproto.WSConnection.state`.

    Fields:

    .. attribute:: code

       (Required) The integer close code to indicate why the connection
       has closed.

    .. attribute:: reason

       Additional reasoning for why the connection has closed.

    """

    code: int
    reason: Optional[str] = None

    def response(self) -> "CloseConnection":
        """Generate an RFC-compliant close frame to send back to the peer."""
        return CloseConnection(code=self.code, reason=self.reason)


T = TypeVar("T", bytes, str)


@dataclass(frozen=True)
class Message(Event, Generic[T]):
    """The websocket data message.

    Fields:

    .. attribute:: data

       (Required) The message data as byte string, can be decoded as UTF-8 for
       TEXT messages.  This only represents a single chunk of data and
       not a full WebSocket message.  You need to buffer and
       reassemble these chunks to get the full message.

    .. attribute:: frame_finished

       This has no semantic content, but is provided just in case some
       weird edge case user wants to be able to reconstruct the
       fragmentation pattern of the original stream.

    .. attribute:: message_finished

       True if this frame is the last one of this message, False if
       more frames are expected.

    """

    data: T
    frame_finished: bool = True
    message_finished: bool = True


@dataclass(frozen=True)
class TextMessage(Message[str]):  # pylint: disable=unsubscriptable-object
    """This event is fired when a data frame with TEXT payload is received.

    Fields:

    .. attribute:: data

       The message data as string, This only represents a single chunk
       of data and not a full WebSocket message.  You need to buffer
       and reassemble these chunks to get the full message.

    """

    # https://github.com/python/mypy/issues/5744
    data: str


@dataclass(frozen=True)
class BytesMessage(Message[bytes]):  # pylint: disable=unsubscriptable-object
    """This event is fired when a data frame with BINARY payload is
    received.

    Fields:

    .. attribute:: data

       The message data as byte string, can be decoded as UTF-8 for
       TEXT messages.  This only represents a single chunk of data and
       not a full WebSocket message.  You need to buffer and
       reassemble these chunks to get the full message.
    """

    # https://github.com/python/mypy/issues/5744
    data: bytes


@dataclass(frozen=True)
class Ping(Event):
    """The Ping event can be sent to trigger a ping frame and is fired
    when a Ping is received.

    **wsproto does not automatically send a pong response to a ping event.** To
    comply with the RFC you MUST send a pong even as soon as is practical. The
    :meth:`response` method provides a suitable event for this purpose.

    Fields:

    .. attribute:: payload

       An optional payload to emit with the ping frame.
    """

    payload: bytes = b""

    def response(self) -> "Pong":
        """Generate an RFC-compliant :class:`Pong` response to this ping."""
        return Pong(payload=self.payload)


@dataclass(frozen=True)
class Pong(Event):
    """The Pong event is fired when a Pong is received.

    Fields:

    .. attribute:: payload

       An optional payload to emit with the pong frame.

    """

    payload: bytes = b""
