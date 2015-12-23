===============
Draft ASGI Spec
===============

**NOTE: This is still heavily in-progress, and should not even be
considered draft yet. Even the name might change; this is being written
as development progresses.**

::

    PEP: XXX
    Title: ASGI (Asynchronous Server Gateway Interface)
    Version: $Revision$
    Last-Modified: $Date$
    Author: Andrew Godwin <andrew@aeracode.org>
    Status: Draft
    Type: Informational
    Content-Type: text/x-rst
    Created: ?
    Post-History: ?

Abstract
========

This document proposes a standard interface between network protocol
servers (particularly webservers) and Python applications, intended
to allow handling of multiple common protocol styles (including HTTP, HTTP2,
and WebSocket).

It is intended to replace and expand on WSGI, though the design
deliberately includes provisions to allow WSGI-to-ASGI and ASGI-to-WGSI
adapters to be easily written for the HTTP protocol.


Rationale
=========

The WSGI specification has worked well since it was introduced, and
allowed for great flexibility in Python framework and webserver choice.
However, its design is irrevocably tied to the HTTP-style
request/response cycle, and more and more protocols are becoming a
standard part of web programming that do not follow this pattern
(most notably, WebSocket).

ASGI attempts to preserve a simple application interface, but provide
an abstraction that allows for data to be sent and received at any time,
and from different application threads or processes.

It also lays out new, serialization-compatible formats for things like
HTTP requests and responses and WebSocket data frames, to allow these to
be transported over a network or local socket, and allow separation
of protocol handling and application logic into different processes.

Part of this design is ensuring there is an easy path to use both
existing WSGI servers and applications, as a large majority of Python
web usage relies on WSGI and providing an easy path forwards is critical
to adoption.


Overview
========

ASGI consists of three different components - *protocol servers*,
a *channel layer*, and *application code*. Channel layers are the core
part of the implementation, and provide an interface to both protocol
servers and applications.

A channel layer provides a protocol server or an application server
with a ``send`` callable, which takes a channel name and message
``dict``, and a ``receive_many`` callable, which takes a list of
channel names and returns the next message available on any named channel.

Thus, rather than under WSGI, where you point the protocol server to the
application, under ASGI you point both the protocol server and the application
to a channel layer instance. It is intended that applications and protocol
servers always run in separate processes or threads, and always communicate
via the channel layer.

Despite the name of the proposal, ASGI does not specify or design to any
specific in-process async solution, such as ``asyncio``, ``twisted``, or
``gevent``. Instead, the ``receive_many`` function is nonblocking - it either
returns ``None`` or a ``(channel, message)`` tuple immediately. This approach
should work with either synchronous or asynchronous code; part of the design
of ASGI is to allow developers to still write synchronous code where possible,
as this makes for easier maintenance and less bugs, at the cost of performance.

The distinction between protocol servers and applications in this document
is mostly to distinguish their roles and to make illustrating concepts easier.
There is no code-level distinction between the two, and it's entirely possible
to have a process that does both, or middleware-like code that transforms
messages between two different channel layers or channel names. It is
expected, however, that most deployments will fall into this pattern.


Channels and Messages
---------------------

All communication in an ASGI stack uses *messages* sent over *channels*.
All messages must be a ``dict`` at the top level of the object, and be
serializable by the built-in ``json`` serializer module (though the
actual serialization a channel layer uses is up to the implementation;
we use ``json`` as the lowest common denominator).

Channels are identified by a byte string name consisting only of ASCII
letters, numbers, numerical digits, periods (``.``), dashes (``-``)
and underscores (``_``), plus an optional prefix character (see below).

Channels are a first-in, first out queue with at-most-once delivery
semantics. They can have multiple writers and multiple readers; only a single
reader should get each written message. Implementations should never
deliver a message more than once or to more than one reader, and should
drop messages if this is necessary to achieve this restriction.

In order to aid with scaling and network architecture, a distinction
is made between channels that have multiple readers (such as the
``http.request`` channel that web applications would listen on from every
application worker process) and *single-reader channels*
(such as a ``http.response.ABCDEF`` channel tied to a client socket).

*Single-reader channel* names are prefixed with an exclamation mark
(``!``) character in order to indicate to the channel layer that it may
have to route these channels' data differently to ensure it reaches the
single process that needs it; these channels are nearly always tied to
incoming connections from the outside world. Some channel layers may not
need this, and can simply treat the prefix as part of the name.

Messages should expire after a set time sitting unread in a channel;
the recommendation is one minute, though the best value depends on the
channel layer and the way it is deployed.

Message size is finite, though the maximum varies based on the channel layer
and the encoding it's using. Channel layers may reject messages at ``send()``
time with a ``MessageTooLarge`` exception; the calling code should take
appropriate action (e.g. HTTP responses can be chunked, while HTTP
requests should be closed with a ``413 Request Entity Too Large`` response).
It is intended that some channel layers will only support messages of around a
megabyte, while others will be able to take a gigabyte or more, and that it
may be configurable.

Handling Protocols
------------------

ASGI messages represent two main things - internal application events
(for example, a channel might be used to queue thumbnails of previously
uploaded videos), and protocol events to/from connected clients.

As such, this specification outlines encodings to and from ASGI messages
for three common protocols (HTTP, WebSocket and raw UDP); this allows any ASGI
web server to talk to any ASGI web application, and the same for any other
protocol with a common specification. It is recommended that if other
protocols become commonplace they should gain standardized formats in a
supplementary specification of their own.

The message formats are a key part of the specification; without them,
the protocol server and web application might be able to talk to each other,
but may not understand some of what the other is saying. It's equivalent to the
standard keys in the ``environ`` dict for WSGI.

The design pattern is that most protocols will share a few channels for
incoming data (for example, ``http.request``, ``websocket.connect`` and
``websocket.receive``), but will have individual channels for sending to
each client (such as ``!http.response.kj2daj23``). This allows incoming
data to be dispatched into a cluster of application servers that can all
handle it, while responses are routed to the individual protocol server
that has the other end of the client's socket.

Some protocols, however, do not have the concept of a unique socket
connection; for example, an SMS gateway protocol server might just have
``sms.receive`` and ``sms.send``, and the protocol server cluster would
take messages from ``sms.send`` and route them into the normal phone
network based on attributes in the message (in this case, a telephone
number).


Extensions
----------

ASGI has the concept of *extensions*, of which one is specified in this
document. Extensions are functionality that is
not required for basic application code and nearly all protocol server
code, and so has been made optional in order to encourage lighter-weight
channel layers to be written.

The only extension in this document is the ``groups`` extension, defined
below.

There is potential to add further extensions; these may be defined by
a separate specification, or a new version of this specification.

If application code requires an extension, it should check for it as soon
as possible, and hard error if it is not provided. Frameworks should
encourage optional use of extensions, while attempting to move any
extension-not-found errors to process startup rather than message handling.


Groups
------

While the basic channel model is sufficient to handle basic application
needs, many more advanced uses of asynchronous messaging require
notifying many users at once when an event occurs - imagine a live blog,
for example, where every viewer should get a long poll response or
WebSocket packet when a new entry is posted.

This concept could be kept external to the ASGI spec, and would be, if it
were not for the significant performance gains a channel layer implementation
could make on the send-group operation by having it included - the
alternative being a ``send_many`` callable that might have to take
tens of thousands of destination channel names in a single call. However,
the group feature is still optional; its presence is indicated by the
``supports_groups`` attribute on the channel layer object.

Thus, there is a simple Group concept in ASGI, which acts as the
broadcast/multicast mechanism across channels. Channels are added to a group,
and then messages sent to that group are sent to all members of the group.
Channels expire from being in a group after a certain amount of time,
and must be refreshed periodically to remain in it, and can also be
explicitly removed.

The expiry is because this specification assumes that at some point
message delivery will fail, and so disconnection events by themselves
are not sufficient to tie to an explicit group removal - over time, the
number of group members will slowly increase as old response channels
leak as disconnections get dropped.

Instead, all protocol servers that have an ongoing connection
(for example, long-poll HTTP or WebSockets) will instead send periodic
"keepalive" messages, which can be used to refresh the response channel's
group membership - each call to ``group_add`` should reset the expiry timer.

Keepalive message intervals should be one-third as long as the group expiry
timeout, to allow for slow or missed delivery of keepalives; protocol servers
and anything else sending keepalives can retrieve the group expiry time from
the channel layer in order to do this correctly.

*Implementation of the group functionality is optional*. If it is not provided
and an application or protocol server requires it, they should hard error
and exit with an appropriate error message. It is expected that protocol
servers will not need to use groups.


Linearization
-------------

The design of ASGI is meant to enable a shared-nothing architecture,
where messages can be handled by any one of a set of threads, processes
or machines running application code.

This, of course, means that several different copies of the application
could be handling messages simultaneously, and those messages could even
be from the same client; in the worst case, two packets from a client
could even be processed out-of-order if one server is slower than another.

This is an existing issue with things like WSGI as well - a user could
open two different tabs to the same site at once and launch simultaneous
requests to different servers - but the nature of the new protocols
specified here mean that collisions are more likely to occur.

Solving this issue is left to frameworks and application code; there are
already solutions such as database transactions that help solve this,
and the vast majority of application code will not need to deal with this
problem. If ordering of incoming packets matters for a protocol, they should
be annotated with a packet number (as WebSocket is in this specification).

Single-reader channels, such as those used for response channels back to
clients, are not subject to this problem; a single reader should always
receive messages in channel order.


Specification Details
=====================

A *channel layer* should provide an object with these attributes
(all function arguments are positional):

* ``send(channel, message)``, a callable that takes two arguments; the
  channel to send on, as a byte string, and the message
  to send, as a serializable ``dict``.

* ``receive_many(channels)``, a callable that takes a list of channel
  names as byte strings, and returns immediately with either ``None``
  or ``(channel, message)`` if a message is available.

* ``new_channel(format)``, a callable that takes a byte string pattern,
  and returns a new valid channel name that does not already exist, by
  substituting any occurrences of the question mark character ``?`` in
  ``format`` with a single random byte string and checking for
  existence of that name in the channel layer. This is NOT called prior to
  a message being sent on a channel, and should not be used for channel
  initialization.

* ``MessageTooLarge``, the exception raised when a send operation fails
  because the encoded message is over the layer's size limit.

* ``extensions``, a list of byte string names indicating which
  extensions this layer provides, or empty if it supports none.
  The only valid extension name is ``groups``.

A channel layer implementing the ``groups`` extension must also provide:

* ``group_add(group, channel)``, a callable that takes a ``channel`` and adds
  it to the group given by ``group``. Both are byte strings.

* ``group_discard(group, channel)``, a callable that removes the ``channel``
  from the ``group`` if it is in it, and does nothing otherwise.

* ``send_group(group, message)``, a callable that takes two positional
  arguments; the group to send to, as a byte string, and the message
  to send, as a serializable ``dict``.

* ``group_expiry``, an integer number of seconds describing the minimum
  group membership age before a channel is removed from a group.


Channel Semantics
-----------------

Channels **must**:

* Preserve ordering of messages perfectly with only a single reader
  and writer, and preserve as much as possible in other cases.

* Never deliver a message more than once.

* Never block on message send.

* Be able to handle messages of at least 1MB in size when encoded as
  JSON (the implementation may use better encoding or compression, as long
  as it meets the equivalent size)

* Have a maximum name length of at least 100 bytes.

They are not expected to deliver all messages, but a success rate of at least
99.99% is expected under normal circumstances. Implementations may want to
have a "resilience testing" mode where they deliberately drop more messages
than usual so developers can test their code's handling of these scenarios.


Message Formats
---------------

These describe the standardized message formats for the protocols this
specification supports. All messages are ``dicts`` at the top level,
and all keys are required unless otherwise specified (with a default to
use if the key is missing).

The one common key across all protocols is ``reply_channel``, a way to indicate
the client-specific channel to send responses to. Protocols are generally
encouraged to have one message type and one reply channel to ensure ordering.

Messages are specified here along with the channel names they are expected
on; if a channel name can vary, such as with reply channels, the varying
portion will be replaced by ``?``, such as ``http.response.?``, which matches
the format the ``new_channel`` callable takes.

There is no label on message types to say what they are; their type is implicit
in the channel name they are received on. Two types that are sent on the same
channel, such as HTTP responses and server pushes, are distinguished apart
by their required fields.


HTTP
----

The HTTP format covers HTTP/1.0, HTTP/1.1 and HTTP/2, as the changes in
HTTP/2 are largely on the transport level. A protocol server should give
different requests on the same connection different reply channels, and
correctly multiplex the responses back into the same stream as they come in.
The HTTP version is available as a string in the request message.

HTTP/2 Server Push responses are included, but should be sent prior to the
main response, and you should check for ``http_version = 2`` before sending
them; if a protocol server or connection incapable of Server Push receives
these, it should simply drop them.

The HTTP specs are somewhat vague on the subject of multiple headers;
RFC7230 explicitly says they must be mergeable with commas, while RFC6265
says that ``Set-Cookie`` headers cannot be combined this way. This is why
request ``headers`` is a ``dict``, and response ``headers`` is a list of
tuples, which matches WSGI.

Request
'''''''

Sent once for each request that comes into the protocol server.

Channel: ``http.request``

Keys:

* ``reply_channel``: Channel name for responses and server pushes, in
  format ``http.response.?``

* ``http_version``: Byte string, one of ``1.0``, ``1.1`` or ``2``.

* ``method``: Byte string HTTP method name, uppercased.

* ``scheme``: Byte string URL scheme portion (likely ``http`` or ``https``).
  Optional (but must not be empty), default is ``http``.

* ``path``: Byte string HTTP path from URL.

* ``query_string``: Byte string URL portion after the ``?``. Optional, default
  is empty string.

* ``root_path``: Byte string that indicates the root path this application
  is mounted at; same as ``SCRIPT_NAME`` in WSGI. Optional, defaults
  to empty string.

* ``headers``: Dict of ``{name: value}``, where ``name`` is the lowercased
  HTTP header name as byte string and ``value`` is the header value as a byte
  string. If multiple headers with the same name are received, they should
  be concatenated into a single header as per .

* ``body``: Body of the request, as a byte string. Optional, defaults to empty
  string.

* ``client``: List of ``[host, port]`` where ``host`` is a byte string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer. Optional, defaults to ``None``.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a byte string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.


Response
''''''''

Send after any server pushes, and before any response chunks.

Channel: ``http.response.?``

Keys:

* ``status``: Integer HTTP status code. 

* ``status_text``: Byte string HTTP reason-phrase, e.g. ``OK`` from ``200 OK``.
  Ignored for HTTP/2 clients. Optional, default should be based on ``status``
  or left as empty string if no default found.

* ``headers``: A list of ``[name, value]`` pairs, where ``name`` is the byte
  string header name, and ``value`` is the byte string header value. Order
  should be preserved in the HTTP response.

* ``content``: Byte string of HTTP body content

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Response Chunk message). If ``False``, response will
  be taken as complete and closed off, and any further messages on the channel
  will be ignored. Optional, defaults to ``False``.


Response Chunk
''''''''''''''

Must be sent after an initial Response.

Channel: ``http.response.?``

Keys:

* ``content``: Byte string of HTTP body content, will be concatenated onto
  previously received ``content`` values.

* ``more_content``: Boolean value signifying if there is additional content
  to come (as part of a Response Chunk message). If ``False``, response will
  be taken as complete and closed off, and any further messages on the channel
  will be ignored. Optional, defaults to ``False``.


Server Push
'''''''''''

Send before any Response or Response Chunk. HTTP/2 only.

TODO


WebSocket
---------

WebSockets share some HTTP details - they have a path and headers - but also
have more state. Path and header details are only sent in the connection
message; applications that need to refer to these during later messages
should store them in a cache or database.

WebSocket protocol servers should handle PING/PONG requests themselves, and
send PING frames as necessary to ensure the connection is alive.


Connection
''''''''''

Sent when the client initially opens a connection and completes the
WebSocket handshake.

Channel: ``websocket.connect``

Keys:

* ``reply_channel``: Channel name for sending data, in
  format ``websocket.send.?``

* ``scheme``: Byte string URL scheme portion (likely ``ws`` or ``wss``).
  Optional (but must not be empty), default is ``ws``.

* ``path``: Byte string HTTP path from URL.

* ``query_string``: Byte string URL portion after the ``?``. Optional, default
  is empty string.

* ``root_path``: Byte string that indicates the root path this application
  is mounted at; same as ``SCRIPT_NAME`` in WSGI. Optional, defaults
  to empty string.

* ``headers``: Dict of ``{name: value}``, where ``name`` is the lowercased
  HTTP header name as byte string and ``value`` is the header value as a byte
  string. If multiple headers with the same name are received, they should
  be concatenated into a single header as per .

* ``client``: List of ``[host, port]`` where ``host`` is a byte string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer. Optional, defaults to ``None``.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a byte string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.


Receive
'''''''

Sent when a data frame is received from the client.

Channel: ``websocket.receive``

Keys:

* ``reply_channel``: Channel name for sending data, in
  format ``websocket.send.?``

* ``bytes``: Byte string of frame content, if it was bytes mode, or ``None``.

* ``text``: Unicode string of frame content, if it was text mode, or ``None``.

One of ``bytes`` or ``text`` must be non-``None``.


Disconnection
'''''''''''''

Sent when either connection to the client is lost, either from the client
closing the connection, the server closing the connection, or loss of the
socket.

Channel: ``websocket.disconnect``

Keys:

* ``reply_channel``: Channel name that was used for sending data, in
  format ``websocket.send.?``. Cannot be used to send at this point; provided
  as a way to identify the connection only.


Send/Close
''''''''''

Sends a data frame to the client and/or closes the connection from the
server end.

Channel: ``websocket.send.?``

Keys:

* ``bytes``: Byte string of frame content, if in bytes mode, or ``None``.

* ``text``: Unicode string of frame content, if in text mode, or ``None``.

* ``close``: Boolean saying if the connection should be closed after data
  is sent, if any. Optional, default ``False``.

A maximum of one of ``bytes`` or ``text`` may be provided. If both are
provided, the protocol server should ignore the message entirely.


UDP
---

Raw UDP is included here as it is a datagram-based, unordered and unreliable
protocol, which neatly maps to the underlying message abstraction. It is not
expected that many applications would use the low-level protocol, but it may
be useful for some.

While it might seem odd to have reply channels for UDP as it is a stateless
protocol, replies need to come from the same server as the messages were
sent to, so the reply channel here ensures that reply packets from an ASGI
stack do not come from a different protocol server to the one you sent the
initial packet to.


Receive
'''''''

Sent when a UDP datagram is received.

Channel: ``udp.receive``

Keys:

* ``reply_channel``: Channel name for sending data, in format ``udp.send.?``

* ``data``: Byte string of UDP datagram payload.

* ``client``: List of ``[host, port]`` where ``host`` is a byte string of the
  remote host's IPv4 or IPv6 address, and ``port`` is the remote port as an
  integer.

* ``server``: List of ``[host, port]`` where ``host`` is the listening address
  for this server as a byte string, and ``port`` is the integer listening port.
  Optional, defaults to ``None``.


Send
''''

Sent to send out a UDP datagram to a client.

Channel: ``udp.send.?``

Keys:

* ``data``: Byte string of UDP datagram payload.


Approximate Global Ordering
---------------------------

While maintaining true global (across-channels) ordering of messages is
entirely unreasonable to expect of many implementations, they should strive
to prevent busy channels from overpowering quiet channels.

For example, imagine two channels, ``busy``, which spikes to 1000 messages a
second, and ``quiet``, which gets one message a second. There's a single
consumer running ``receive_many(['busy', 'quiet'])`` which can handle
around 200 messages a second.

In a simplistic for-loop implementation, the channel layer might always check
``busy`` first; it always has messages available, and so the consumer never
even gets to see a message from ``quiet``, even if it was sent with the
first batch of ``busy`` messages.

A simple way to solve this is to randomize the order of the channel list when
looking for messages inside the channel layer; other, better methods are also
available, but whatever is chosen, it should try to avoid a scenario where
a message doesn't get received purely because another channel is busy.


Strings and Unicode
-------------------

In this document, *byte string* refers to ``str`` on Python 2 and ``bytes``
on Python 3. If this type still supports Unicode codepoints due to the
underlying implementation, then any values should be kept within the lower
8-byte range.

*Unicode string* refers to ``unicode`` on Python 2 and ``str`` on Python 3.
This document will never specify just *string* - all strings are one of the
two types.

Channel and group names are always byte strings, with the additional limitation
that they only use the following characters:

* ASCII letters
* The digits ``0`` through ``9``
* Hyphen ``-``
* Underscore ``_``
* Period ``.``
* Exclamation mark ``!`` (only at the start of a channel name)


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
* ``REMOTE_HOST`` and ``REMOTE_PORT`` are in ``client``
* ``SERVER_PROTOCOL`` is encoded in ``http_version``
* ``wsgi.url_scheme`` is ``scheme``
* ``wsgi.input`` is a StringIO around ``body``
* ``wsgi.errors`` is directed by the wrapper as needed

The ``start_response`` callable maps similarly to Response:

* The ``status`` argument becomes ``status`` and ``status_text``
* ``response_headers`` maps to ``headers``

The main difference is that ASGI is incapable of performing streaming
of HTTP body input, and instead must buffer it all into a message first.


Common Questions
================

1. Why are messages ``dicts``, rather than a more advanced type?

   We want messages to be very portable, especially across process and
   machine boundaries, and so a simple encodable type seemed the best way.
   We expect frameworks to wrap each protocol-specific set of messages in
   custom classes (e.g. ``http.request`` messages become ``Request`` objects)


TODOs
=====

* Work out if we really can just leave HTTP body as byte string. Seems too big.
  Might need some reverse-single-reader chunking? Or just say channel layer
  message size dictates body size.

* Maybe remove ``http_version`` and replace with ``supports_server_push``?

* Be sure we want to leave HTTP ``get`` and ``post`` out.


Copyright
=========

This document has been placed in the public domain.
