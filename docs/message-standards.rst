Message Standards
=================

Some standardised message formats are used for common message types - they
are detailed below. Message formats are meant to be generic and offload as
much protocol-specific processing to the interface server as is reasonable;
thus, they should generally represent things at as high a level as makes sense.

In addition to the standards outlined below, each message may contain a
``reply_channel``, which details where to send responses. Protocols with
separate connection and data receiving messages (like WebSockets) will only
contain the connection and detailed client information in the first message;
use the ``@channel_session`` decorator to persist this data to consumers of
the received data (or something else based on ``reply_channel``).

All messages must be able to be encoded as JSON; channel backends don't
necessarily have to use JSON, but we consider it the lowest common denominator
for serialisation format compatability.

The size limit on messages is 1MB (while channel backends may support larger
sizes, all message formats should stay under this limit, which might include
multi-part messages where large content must be transferred).

The length limit on channel names is 200 printable ASCII characters.


HTTP Request
------------

Represents a full-fledged, single HTTP request coming in from a client.

Standard channel name is ``http.request``.

Contains the following keys:

* get: Dict of {key: [value, ...]} of GET variables (keys and values are strings)
* post: Dict of {key: [value, ...]} of POST variables (keys and values are strings)
* cookies: Dict of cookies as {cookie_name: cookie_value} (names and values are strings)
* meta: Dict of HTTP headers and info as defined in the Django Request docs (names and values are strings)
* path: String, full path to the requested page, without query string or domain
* method: String, upper-cased HTTP method

Should come with an associated ``reply_channel`` which accepts HTTP Responses.


HTTP Response
-------------

Sends either a part of a response or a whole response to a HTTP client - to do
streaming responses, several response messages are sent with ``more_content: True``
and the final one has the key omitted. Normal, single-shot responses do not
need the key at all.

Due to the 1MB size limit on messages, some larger responses will have to be
sent multi-part to stay within the limit.

Only sent on reply channels.

Keys that must only be in the first message of a set:

* content_type: String, mimetype of content
* status: Integer, numerical HTTP status code
* cookies: List of cookies to set (as encoded cookie strings suitable for headers)
* headers: Dictionary of headers (key is header name, value is value, both strings)

All messages in a set can the following keys:

* content: String of content to send
* more_content: Boolean, signals the interface server should wait for another response chunk to stream.


HTTP Disconnect
---------------

Send when a client disconnects early, before the response has been sent.
Only sent by long-polling-capable HTTP interface servers.

Standard channel name is ``http.disconnect``.

Contains no keys.


WebSocket Connection
--------------------

Sent when a new WebSocket is connected.

Standard channel name is ``websocket.connect``.

Contains the same keys as HTTP Request, without the ``POST`` or ``method`` keys.


WebSocket Receive
-----------------

Sent when a datagram is received on the WebSocket.

Standard channel name is ``websocket.receive``.

Contains the following keys:

* content: String content of the datagram.
* binary: Boolean, saying if the content is binary. If not present or false, content is a UTF8 string.


WebSocket Client Close
----------------------

Sent when the WebSocket is closed by either the client or the server.

Standard channel name is ``websocket.disconnect``.

Contains no keys.


WebSocket Send/Close
--------------------

Sent by a Django consumer to send a message back over the WebSocket to
the client or close the client connection. The content is optional if close
is set, and close will happen after any content is sent, if some is present.

Only sent on reply channels.

Contains the keys:

* content: String content of the datagram.
* binary: If the content is to be interpreted as text or binary.
* close: Boolean. If set to True, will close the client connection.
