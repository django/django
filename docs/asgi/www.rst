=================================================
HTTP & WebSocket ASGI Message Format (Draft Spec)
=================================================

.. note::
  This is still in-progress, but is now mostly complete.

The HTTP+WebSocket ASGI sub-specification outlines how to transport HTTP/1.1,
HTTP/2 and WebSocket connections over an ASGI-compatible channel layer.

It is deliberately intended and designed to be a superset of the WSGI format
and specifies how to translate between the two for the set of requests that
are able to be handled by WSGI.

HTTP
----

The HTTP format covers HTTP/1.0, HTTP/1.1 and HTTP/2, as the changes in
HTTP/2 are largely on the transport level. A protocol server should give
different requests on the same connection different reply channels, and
correctly multiplex the responses back into the same stream as they come in.
The HTTP version is available as a string in the request message.

Multiple header fields with the same name are complex in HTTP. RFC 7230
states that for any header field that can appear multiple times, it is exactly
equivalent to sending that header field only once with all the values joined by
commas.

However, RFC 7230 and RFC 6265 make it clear that this rule does not apply to
the various headers used by HTTP cookies (``Cookie`` and ``Set-Cookie``). The
``Cookie`` header must only be sent once by a user-agent, but the
``Set-Cookie`` header may appear repeatedly and cannot be joined by commas.
The ASGI design decision is to transport both request and response headers as
lists of 2-element ``[name, value]`` lists and preserve headers exactly as they
were provided.

The HTTP protocol should be signified to ASGI applications with a ``type`` value
of ``http``.


Connection Scope
''''''''''''''''

HTTP connections have a single-request connection scope - that is, your
applications will be instantiated at the start of the request, and destroyed
at the end, even if the underlying socket is still open and serving multiple
requests.

The connection scope contains:

* ``type``: ``http``

* ``http_version``: Unicode string, one of ``1.0``, ``1.1`` or ``2``.

* ``method``: Unicode string HTTP method name, uppercased.

* ``scheme``: Unicode string URL scheme portion (likely ``http`` or ``https``).
  Optional (but must not be empty), default is ``"http"``.

* ``path``: Unicode string HTTP path from URL, with percent escapes decoded
  and UTF8 byte sequences decoded into characters.

* ``query_string``: Byte string URL portion after the ``?``, not url-decoded.

* ``root_path``: Unicode string that indicates the root path this application
  is mounted at; same as ``SCRIPT_NAME`` in WSGI. Optional, defaults
  to ``""``.

* ``headers``: A list of ``[name, value]`` lists, where ``name`` is the
  byte string header name, and ``value`` is the byte string
  header value. Order of header values must be preserved from the original HTTP
  request; order of header names is not important. Duplicates are possible and
  must be preserved in the message as received.
  Header names must be lowercased.

* ``client``: List of ``[host, port]`` where ``host`` is a unicode string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer. Optional, defaults to ``None``.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a unicode string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.



Request
'''''''

Sent to indicate an incoming request. Most of the request information is in
the connection scope; the body message serves as a way to stream large incoming
HTTP bodies in chunks, and as a trigger to actually run request code (as you
cannot trigger on a connection opening alone).

Keys:

* ``type``: ``http.request``

* ``body``: Body of the request, as a byte string. Optional, defaults to ``""``.
  If ``more_content`` is set, treat as start of body and concatenate
  on further chunks.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Request Body Chunk message). If ``True``, the consuming
  application should wait until it gets a chunk with this set to ``False``. If
  ``False``, the request is complete and should be processed.


Response
''''''''

Starts, or continues, sending a response to the client. Protocol servers must
flush any data passed to them into the send buffer before returning from a
send call.

Keys:

* ``type``: ``http.response``

* ``status``: Integer HTTP status code.

* ``headers``: A list of ``[name, value]`` lists, where ``name`` is the
  byte string header name, and ``value`` is the byte string
  header value. Order must be preserved in the HTTP response. Header names
  must be lowercased. Optional, defaults to an empty list. Only allowed on
  the first response message.

* ``content``: Byte string of HTTP body content. Concatenated onto any previous
  ``content`` values sent in this connection scope. Optional, defaults to
  ``""``.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Response message). If ``False``, response will
  be taken as complete and closed off, and any further messages on the channel
  will be ignored. Optional, defaults to ``False``.


Disconnect
''''''''''

Sent when a HTTP connection is closed. This is mainly useful for long-polling,
where you may want to trigger cleanup code if the connection closes early.

Keys:

* ``type``: ``http.disconnect``


WebSocket
---------

WebSockets share some HTTP details - they have a path and headers - but also
have more state. Path and header details are only sent in the connection
message; applications that need to refer to these during later messages
should store them in a cache or database.

WebSocket protocol servers should handle PING/PONG requests themselves, and
send PING frames as necessary to ensure the connection is alive.

The WebSocket protocol should be signified to ASGI applications with
a ``type`` value of ``websocket``.


Connection Scope
''''''''''''''''

WebSocket connections' scope lives as long as the socket itself - if the
application dies the socket should be closed, and vice-versa. The scope
contains the initial connection metadata (mostly from HTTP headers):

* ``type``: ``websocket``

* ``scheme``: Unicode string URL scheme portion (likely ``ws`` or ``wss``).
  Optional (but must not be empty), default is ``ws``.

* ``path``: Unicode HTTP path from URL, already urldecoded.

* ``query_string``: Byte string URL portion after the ``?``. Optional, default
  is empty string.

* ``root_path``: Byte string that indicates the root path this application
  is mounted at; same as ``SCRIPT_NAME`` in WSGI. Optional, defaults
  to empty string.

* ``headers``: List of ``[name, value]``, where ``name`` is the
  header name as byte string and ``value`` is the header value as a byte
  string. Order should be preserved from the original HTTP request;
  duplicates are possible and must be preserved in the message as received.
  Header names must be lowercased.

* ``client``: List of ``[host, port]`` where ``host`` is a unicode string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer. Optional, defaults to ``None``.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a unicode string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.

* ``subprotocols``: List of subprotocols the client advertised as unicode strings.
  Optional, defaults to empty list.



Connection
''''''''''

Sent when the client initially opens a connection and is about to finish the
WebSocket handshake.

This message must be responded to with either an *Accept* message
or a *Close* message before the socket will pass ``websocket.receive``
messages. The protocol server must ideally send this message
during the handshake phase of the WebSocket and not complete the handshake
until it gets a reply, returning HTTP status code ``403`` if the connection is
denied.

Keys:

* ``type``: ``websocket.connect``


Accept
''''''

Sent by the application when it wishes to accept an incoming connection.

* ``type``: ``websocket.accept``

* ``subprotocol``: The subprotocol the server wishes to accept, as a unicode
  string. Optional, defaults to ``None``.


Receive
'''''''

Sent when a data frame is received from the client.

Keys:

* ``type``: ``websocket.receive``

* ``bytes``: Byte string of frame content, if it was binary mode, or ``None``.

* ``text``: Unicode string of frame content, if it was text mode, or ``None``.

Exactly one of ``bytes`` or ``text`` must be non-``None``.


Send
''''

Sends a data frame to the client.

Keys:

* ``type``: ``websocket.send``

* ``bytes``: Byte string of binary frame content, or ``None``.

* ``text``: Unicode string of text frame content, or ``None``.

Exactly one of ``bytes`` or ``text`` must be non-``None``.


Disconnection
'''''''''''''

Sent when either connection to the client is lost, either from the client
closing the connection, the server closing the connection, or loss of the
socket.

Keys:

* ``type``: ``websocket.disconnect``

* ``code``: The WebSocket close code (integer), as per the WebSocket spec.


Close
'''''

* ``type``: ``websocket.close``

* ``code``: The WebSocket close code (integer), as per the WebSocket spec.
  Optional, defaults to ``1000``.



WSGI Compatibility
------------------

Part of the design of the HTTP portion of this spec is to make sure it
aligns well with the WSGI specification, to ensure easy adaptability
between both specifications and the ability to keep using WSGI servers or
applications with ASGI.

The adaptability works in two ways:

* WSGI to ASGI: A WSGI application can be written that transforms
  ``environ`` into a ``http`` scope and a ``http.request`` message, running the
  application inside a temporary async event loop. This solution would not
  allow full use of async to share CPU between requests, but would allow use
  of existing WSGI servers.

* ASGI to WSGI: An ASGI application can be written that translates the
  ``http`` scope and ``http.request`` message down into a WSGI ``environ``
  and calls it inside a threadpool.

There is an almost direct mapping for the various special keys in
WSGI's ``environ`` variable to the ``http`` scope:

* ``REQUEST_METHOD`` is the ``method`` key
* ``SCRIPT_NAME`` is ``root_path``
* ``PATH_INFO`` can be derived from ``path`` and ``root_path``
* ``QUERY_STRING`` is ``query_string``
* ``CONTENT_TYPE`` can be extracted from ``headers``
* ``CONTENT_LENGTH`` can be extracted from ``headers``
* ``SERVER_NAME`` and ``SERVER_PORT`` are in ``server``
* ``REMOTE_HOST``/``REMOTE_ADDR`` and ``REMOTE_PORT`` are in ``client``
* ``SERVER_PROTOCOL`` is encoded in ``http_version``
* ``wsgi.url_scheme`` is ``scheme``
* ``wsgi.input`` is a StringIO based around the ``http.request`` messages
* ``wsgi.errors`` is directed by the wrapper as needed

The ``start_response`` callable maps similarly to Response:

* The ``status`` argument becomes ``status``, with the reason phrase dropped.
* ``response_headers`` maps to ``headers``

It may even be possible to map Request Body Chunks in a way that allows
streaming of body data, though it would likely be easier and sufficient for
many applications to simply buffer the whole body into memory before calling
the WSGI application.
