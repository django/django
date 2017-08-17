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

HTTP/2 Server Push responses are included, but must be sent prior to the
main response, and applications must check for ``http_version = 2`` before
sending them; if a protocol server or connection incapable of Server Push
receives these, it must drop them.

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


Request
'''''''

Keys:

* ``type``: ``http.request``

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

* ``body``: Body of the request, as a byte string. Optional, defaults to ``""``.
  If ``more_content`` is set, treat as start of body and concatenate
  on further chunks.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Request Body Chunk message). If ``True``, the consuming
  application should wait until it gets a chunk with this set to ``False``. If
  ``False``, the request is complete and should be processed.

* ``client``: List of ``[host, port]`` where ``host`` is a unicode string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer. Optional, defaults to ``None``.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a unicode string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.


Request Body Chunk
''''''''''''''''''

Keys:

* ``type``: ``http.request.body``

* ``content``: Byte string of HTTP body content, will be concatenated onto
  previously received ``content`` values and ``body`` key in Request.
  Not required if ``closed`` is True, required otherwise.

* ``closed``: True if the client closed the connection prematurely and the
  rest of the body. If you receive this, abandon processing of the HTTP request.
  Optional, defaults to ``False``.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Request Body Chunk message). If ``True``, the consuming
  application should wait until it gets a chunk with this set to ``False``. If
  ``False``, the request is complete and should be processed.


Response
''''''''

Send after any server pushes, and before any response chunks.

Keys:

* ``type``: ``http.response``

* ``status``: Integer HTTP status code.

* ``headers``: A list of ``[name, value]`` lists, where ``name`` is the
  byte string header name, and ``value`` is the byte string
  header value. Order must be preserved in the HTTP response. Header names
  must be lowercased. Optional, defaults to an empty list.

* ``content``: Byte string of HTTP body content.
  Optional, defaults to empty string.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Response Chunk message). If ``False``, response will
  be taken as complete and closed off, and any further messages on the channel
  will be ignored. Optional, defaults to ``False``.


Response Chunk
''''''''''''''

Keys:

* ``type``: ``http.response.body``

* ``content``: Byte string of HTTP body content, will be concatenated onto
  previously received ``content`` values.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Response Chunk message). If ``False``, response will
  be taken as complete and closed off, and any further messages on the channel
  will be ignored. Optional, defaults to ``False``.


Server Push
'''''''''''

Must be sent before any Response or Response Chunk messages.

When a server receives this message, it must treat the Request message in the
``request`` field of the Server Push as though it were a new HTTP request being
received from the network. A server may, if it chooses, apply all of its
internal logic to handling this request (e.g. the server may want to try to
satisfy the request from a cache). Regardless, if the server is unable to
satisfy the request itself it must create a new ``http.request`` and ask the
application to serve the request itself.

This approach limits the amount of knowledge the application has to have about
pushed responses: they essentially appear to the application like a normal HTTP
request, with the difference being that the application itself triggered the
request.

If the remote peer does not support server push, either because it's not a
HTTP/2 peer or because SETTINGS_ENABLE_PUSH is set to 0, the server must do
nothing in response to this message.

Keys:

* ``type``: ``http.server_push``

* ``request``: A Request message. The ``body``, ``body_channel``, and
  ``reply_channel`` fields MUST be absent: bodies are not allowed on
  server-pushed requests, and applications should not create reply channels.


Disconnect
''''''''''

Sent when a HTTP connection is closed. This is mainly useful for long-polling,
where you may have added the response channel to a Group or other set of
channels you want to trigger a reply to when data arrives.

Keys:

* ``type``: ``http.disconnect``

* ``path``: Unicode string HTTP path from URL, with percent escapes decoded
  and UTF8 byte sequences decoded into characters.


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


Connection
''''''''''

Sent when the client initially opens a connection and completes the
WebSocket handshake.

This message must be responded to with either an *Accept* message
or a *Close* message before the socket will pass ``websocket.receive``
messages. The protocol server should ideally send this message
during the handshake phase of the WebSocket and not complete the handshake
until it gets a reply, returning HTTP status code ``403`` if the connection is
denied. If this is not possible, it must buffer WebSocket frames and not
send them onto ``websocket.receive`` until a reply is received, and if the
connection is rejected, return WebSocket close code ``4403``.

Channel: ``websocket.connect``

Keys:

* ``type``: ``websocket.connect``

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

* ``order``: The integer value ``0``.


Receive
'''''''

Sent when a data frame is received from the client. If ``ChannelFull`` is
raised, you may retry sending it but if it does not send the socket must
be closed with websocket error code 1013.

Channel: ``websocket.receive``

Keys:

* ``reply_channel``: Channel name for sending data

* ``path``: Path sent during ``connect``, sent to make routing easier for apps.

* ``bytes``: Byte string of frame content, if it was bytes mode, or ``None``.

* ``text``: Unicode string of frame content, if it was text mode, or ``None``.

* ``order``: Order of this frame in the WebSocket stream, starting
  at 1 (``connect`` is 0).

One of ``bytes`` or ``text`` must be non-``None``.


Disconnection
'''''''''''''

Sent when either connection to the client is lost, either from the client
closing the connection, the server closing the connection, or loss of the
socket.

If ``ChannelFull`` is raised, then give up attempting to send the message;
consumption is not required.

Channel: ``websocket.disconnect``

Keys:

* ``reply_channel``: Channel name that was used for sending data.
  Cannot be used to send at this point; provided
  as a way to identify the connection only.

* ``code``: The WebSocket close code (integer), as per the WebSocket spec.

* ``path``: Path sent during ``connect``, sent to make routing easier for apps.

* ``order``: Order of the disconnection relative to the incoming frames'
  ``order`` values in ``websocket.receive``.


Send/Close/Accept
'''''''''''''''''

Sends a data frame to the client and/or closes the connection from the
server end and/or accepts a connection. If ``ChannelFull`` is raised, wait
and try again.

If received while the connection is waiting for acceptance after a ``connect``
message:

* If ``accept`` is ``True``, accept the connection (and send any data provided).
* If ``accept`` is ``False``, reject the connection and do nothing else.
  If ``bytes`` or ``text`` were also present they must be ignored.
* If ``bytes`` or ``text`` is present and contains a non-empty value,
  accept the connection and send the data.
* If ``close`` is ``True`` or a positive integer, reject the connection. If
  ``bytes`` or ``text`` is also set and not empty, it should accept the
  connection,  send the  frame, then immediately close the connection.
  Note that any close code integer sent is ignored, as connections are
  rejected with HTTP's ``403 Forbidden``, unless data is also sent, in which
  case a full WebSocket close is done with the provided code.

If received while the connection is established:

* If ``bytes`` or ``text`` is present, send the data.
* If ``close`` is ``True`` or a positive integer, close the connection after
  any send.
* ``accept`` is ignored.

Channel: Defined by server, suggested ``websocket.send.RANDOMPART!CLIENTID``

Keys:

* ``bytes``: Byte string of frame content, if in bytes mode, or ``None``.

* ``text``: Unicode string of frame content, if in text mode, or ``None``.

* ``close``: Boolean indicating if the connection should be closed after
  data is sent, if any. Alternatively, a positive integer specifying the
  response code. The response code will be 1000 if you pass ``True``.
  Optional, default ``False``.

* ``accept``: Boolean saying if the connection should be accepted without
  sending a frame if it is in the handshake phase.

A maximum of one of ``bytes`` or ``text`` may be provided. If both are
provided, the protocol server should ignore the message entirely.


WSGI Compatibility
------------------

Part of the design of the HTTP portion of this spec is to make sure it
aligns well with the WSGI specification, to ensure easy adaptability
between both specifications and the ability to keep using WSGI servers or
applications with ASGI.

The adaptability works in two ways:

* WSGI Server to ASGI: A WSGI application can be written that transforms
  ``environ`` into a Request message, sends it off on the ``http.request``
  channel, and then waits on a generated response channel for a Response
  message. This has the disadvantage of tying up an entire WSGI thread
  to poll one channel, but should not be a massive performance drop if
  there is no backlog on the request channel, and would work fine for an
  in-process adapter to run a pure-ASGI web application.

* ASGI to WSGI application: A small wrapper process is needed that listens
  on the ``http.request`` channel, and decodes incoming Request messages
  into an ``environ`` dict that matches the WSGI specs, while passing in
  a ``start_response`` that stores the values for sending with the first
  content chunk. Then, the application iterates over the WSGI app,
  packaging each returned content chunk into a Response or Response Chunk
  message (if more than one is yielded).

There is an almost direct mapping for the various special keys in
WSGI's ``environ`` variable to the Request message:

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
* ``wsgi.input`` is a StringIO around ``body``
* ``wsgi.errors`` is directed by the wrapper as needed

The ``start_response`` callable maps similarly to Response:

* The ``status`` argument becomes ``status``, with the reason phrase dropped.
* ``response_headers`` maps to ``headers``

It may even be possible to map Request Body Chunks in a way that allows
streaming of body data, though it would likely be easier and sufficient for
many applications to simply buffer the whole body into memory before calling
the WSGI application.


TODOs
-----

* Maybe remove ``http_version`` and replace with ``supports_server_push``?
