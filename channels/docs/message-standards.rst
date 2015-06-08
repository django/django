Message Standards
=================

Some standardised message formats are used for common message types - they
are detailed below.

Note: All consumers also receive the channel name as the keyword argument
"channel", so there is no need for separate type information to let
multi-channel consumers distinguish.

HTTP Request
------------

Represents a full-fledged, single HTTP request coming in from a client.

Contains the following keys:

* GET: List of (key, value) tuples of GET variables
* POST: List of (key, value) tuples of POST variables
* COOKIES: Same as  ``request.COOKIES``
* META: Same as  ``request.META``
* path: Same as  ``request.path``
* path_info: Same as  ``request.path_info``
* method: Upper-cased HTTP method
* response_channel: Channel name to write response to


HTTP Response
-------------

Sends a whole response to a client.

Contains the following keys:

* content: String of content to send
* content_type: Mimetype of content
* status_code: Numerical HTTP status code
* headers: Dictionary of headers (key is header name, value is value)


HTTP Disconnect
---------------

Send when a client disconnects early, before the response has been sent.
Only sent by long-polling-capable HTTP interface servers.

Contains the same keys as HTTP Request.


WebSocket Connection
--------------------

Sent when a new WebSocket is connected.

Contains the following keys:

* GET: List of (key, value) tuples of GET variables
* COOKIES: Same as ``request.COOKIES``
* META: Same as ``request.META``
* path: Same as ``request.path``
* path_info: Same as  ``request.path_info``
* send_channel: Channel name to send responses on


WebSocket Receive
-----------------

Sent when a datagram is received on the WebSocket.

Contains the same keys as WebSocket Connection, plus:

* content: String content of the datagram


WebSocket Close
---------------

Sent when the WebSocket is closed by either the client or the server.

Contains the same keys as WebSocket Connection, including send_channel,
though nothing should be sent on it.
