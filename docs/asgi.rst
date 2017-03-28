=======================================================
ASGI (Asynchronous Server Gateway Interface) Draft Spec
=======================================================

.. note::
  This is still in-progress, but is now mostly complete.

Abstract
========

This document proposes a standard interface between network protocol
servers (particularly web servers) and Python applications, intended
to allow handling of multiple common protocol styles (including HTTP, HTTP2,
and WebSocket).

This base specification is intended to fix in place the set of APIs by which
these servers interact and the guarantees and style of message delivery;
each supported protocol (such as HTTP) has a sub-specification that outlines
how to encode and decode that protocol into messages.

The set of sub-specifications is available :ref:`in the Message Formats section <asgi_sub_specifications>`.


Rationale
=========

The WSGI specification has worked well since it was introduced, and
allowed for great flexibility in Python framework and web server choice.
However, its design is irrevocably tied to the HTTP-style
request/response cycle, and more and more protocols are becoming a
standard part of web programming that do not follow this pattern
(most notably, WebSocket).

ASGI attempts to preserve a simple application interface, but provide
an abstraction that allows for data to be sent and received at any time,
and from different application threads or processes.

It also take the principle of turning protocols into Python-compatible,
asynchronous-friendly sets of messages and generalises it into two parts;
a standardised interface for communication and to build servers around (this
document), and a set of standard :ref:`message formats for each protocol <asgi_sub_specifications>`.

Its primary goal is to provide a way to write HTTP/2 and WebSocket code,
alongside normal HTTP handling code, however, and part of this design is
ensuring there is an easy path to use both existing WSGI servers and
applications, as a large majority of Python web usage relies on WSGI and
providing an easy path forwards is critical to adoption. Details on that
interoperability are covered in :doc:`/asgi/www`.

The end result of this process has been a specification for generalised
inter-process communication between Python processes, with a certain set of
guarantees and delivery styles that make it suited to low-latency protocol
processing and response. It is not intended to replace things like traditional
task queues, but it is intended that it could be used for things like
distributed systems communication, or as the backbone of a service-oriented
architecure for inter-service communication.


Overview
========

ASGI consists of three different components - *protocol servers*,
a *channel layer*, and *application code*. Channel layers are the core
part of the implementation, and provide an interface to both protocol
servers and applications.

A channel layer provides a protocol server or an application server
with a ``send`` callable, which takes a channel name and message
``dict``, and a ``receive`` callable, which takes a list of
channel names and returns the next message available on any named channel.

Thus, rather than under WSGI, where you point the protocol server to the
application, under ASGI you point both the protocol server and the application
to a channel layer instance. It is intended that applications and protocol
servers always run in separate processes or threads, and always communicate
via the channel layer.

ASGI tries to be as compatible as possible by default, and so the only
implementation of ``receive`` that must be provided is a fully-synchronous,
nonblocking one. Implementations can then choose to implement a blocking mode
in this method, and if they wish to go further, versions compatible with
the asyncio or Twisted frameworks (or other frameworks that may become
popular, thanks to the extension declaration mechanism).

The distinction between protocol servers and applications in this document
is mostly to distinguish their roles and to make illustrating concepts easier.
There is no code-level distinction between the two, and it's entirely possible
to have a process that does both, or middleware-like code that transforms
messages between two different channel layers or channel names. It is
expected, however, that most deployments will fall into this pattern.

There is even room for a WSGI-like application abstraction on the application
server side, with a callable which takes ``(channel, message, send_func)``,
but this would be slightly too restrictive for many use cases and does not
cover how to specify channel names to listen on. It is expected that
frameworks will cover this use case.


Channels and Messages
---------------------

All communication in an ASGI stack uses *messages* sent over *channels*.
All messages must be a ``dict`` at the top level of the object, and
contain only the following types to ensure serializability:

* Byte strings
* Unicode strings
* Integers (within the signed 64 bit range)
* Floating point numbers (within the IEEE 754 double precision range)
* Lists (tuples should be treated as lists)
* Dicts (keys must be unicode strings)
* Booleans
* None

Channels are identified by a unicode string name consisting only of ASCII
letters, ASCII numerical digits, periods (``.``), dashes (``-``) and
underscores (``_``), plus an optional type character (see below).

Channels are a first-in, first out queue with at-most-once delivery
semantics. They can have multiple writers and multiple readers; only a single
reader should get each written message. Implementations must never deliver
a message more than once or to more than one reader, and must drop messages if
this is necessary to achieve this restriction.

In order to aid with scaling and network architecture, a distinction
is made between channels that have multiple readers (such as the
``http.request`` channel that web applications would listen on from every
application worker process), *single-reader channels* that are read from a
single unknown location (such as ``http.request.body?ABCDEF``), and
*process-specific channels* (such as a ``http.response.A1B2C3!D4E5F6`` channel
tied to a client socket).

*Normal channel* names contain no type characters, and can be routed however
the backend wishes; in particular, they do not have to appear globally
consistent, and backends may shard their contents out to different servers
so that a querying client only sees some portion of the messages. Calling
``receive`` on these channels does not guarantee that you will get the
messages in order or that you will get anything if the channel is non-empty.

*Single-reader channel* names contain a question mark
(``?``) character in order to indicate to the channel layer that it must make
these channels appear globally consistent. The ``?`` is always preceded by
the main channel name (e.g. ``http.response.body``) and followed by a
random portion. Channel layers may use the random portion to help pin the
channel to a server, but reads from this channel by a single process must
always be in-order and return messages if the channel is non-empty. These names
must be generated by the ``new_channel`` call.

*Process-specific channel* names contain an exclamation mark (``!``) that
separates a remote and local part. These channels are received differently;
only the name up to and including the ``!`` character is passed to the
``receive()`` call, and it will receive any message on any channel with that
prefix. This allows a process, such as a HTTP terminator, to listen on a single
process-specific channel, and then distribute incoming requests to the
appropriate client sockets using the local part (the part after the ``!``).
The local parts must be generated and managed by the process that consumes them.
These channels, like single-reader channels, are guaranteed to give any extant
messages in order if received from a single process.

Messages should expire after a set time sitting unread in a channel;
the recommendation is one minute, though the best value depends on the
channel layer and the way it is deployed.

The maximum message size is 1MB if the message were encoded as JSON;
if more data than this needs to be transmitted it must be chunked or placed
onto its own single-reader or process-specific channel (see how HTTP request
bodies are done, for example). All channel layers must support messages up
to this size, but protocol specifications are encouraged to keep well below it.


Handling Protocols
------------------

ASGI messages represent two main things - internal application events
(for example, a channel might be used to queue thumbnails of previously
uploaded videos), and protocol events to/from connected clients.

As such, there are :ref:`sub-specifications <asgi_sub_specifications>` that
outline encodings to and from ASGI messages for common protocols like HTTP and
WebSocket; in particular, the HTTP one covers the WSGI/ASGI interoperability.
It is recommended that if a protocol becomes commonplace, it should gain
standardized formats in a sub-specification of its own.

The message formats are a key part of the specification; without them,
the protocol server and web application might be able to talk to each other,
but may not understand some of what the other is saying. It's equivalent to the
standard keys in the ``environ`` dict for WSGI.

The design pattern is that most protocols will share a few channels for
incoming data (for example, ``http.request``, ``websocket.connect`` and
``websocket.receive``), but will have individual channels for sending to
each client (such as ``http.response!kj2daj23``). This allows incoming
data to be dispatched into a cluster of application servers that can all
handle it, while responses are routed to the individual protocol server
that has the other end of the client's socket.

Some protocols, however, do not have the concept of a unique socket
connection; for example, an SMS gateway protocol server might just have
``sms.receive`` and ``sms.send``, and the protocol server cluster would
take messages from ``sms.send`` and route them into the normal phone
network based on attributes in the message (in this case, a telephone
number).


.. _asgi_extensions:

Extensions
----------

Extensions are functionality that is
not required for basic application code and nearly all protocol server
code, and so has been made optional in order to enable lightweight
channel layers for applications that don't need the full feature set defined
here.

The extensions defined here are:

* ``groups``: Allows grouping of channels to allow broadcast; see below for more.
* ``flush``: Allows easier testing and development with channel layers.
* ``statistics``: Allows channel layers to provide global and per-channel statistics.
* ``twisted``: Async compatibility with the Twisted framework.
* ``asyncio``: Async compatibility with Python 3's asyncio.

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
Channels can be removed from a group manually (e.g. based on a disconnect
event), and the channel layer will garbage collect "old" channels in groups
on a periodic basis.

How this garbage collection happens is not specified here, as it depends on
the internal implementation of the channel layer. The recommended approach,
however, is when a message on a process-specific channel expires, the channel
layer should remove that channel from all groups it's currently a member of;
this is deemed an acceptable indication that the channel's listener is gone.

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
be annotated with a packet number (as WebSocket is in its specification).

Single-reader and process-specific channels, such as those used for response
channels back to clients, are not subject to this problem; a single reader
on these must always receive messages in channel order.


Capacity
--------

To provide backpressure, each channel in a channel layer may have a capacity,
defined however the layer wishes (it is recommended that it is configurable
by the user using keyword arguments to the channel layer constructor, and
furthermore configurable per channel name or name prefix).

When a channel is at or over capacity, trying to send() to that channel
may raise ChannelFull, which indicates to the sender the channel is over
capacity. How the sender wishes to deal with this will depend on context;
for example, a web application trying to send a response body will likely
wait until it empties out again, while a HTTP interface server trying to
send in a request would drop the request and return a 503 error.

Sending to a group never raises ChannelFull; instead, it must silently drop
the message if it is over capacity, as per ASGI's at-most-once delivery
policy.


Specification Details
=====================

A *channel layer* must provide an object with these attributes
(all function arguments are positional):

* ``send(channel, message)``, a callable that takes two arguments: the
  channel to send on, as a unicode string, and the message
  to send, as a serializable ``dict``.

* ``receive(channels, block=False)``, a callable that takes a list of channel
  names as unicode strings, and returns with either ``(None, None)``
  or ``(channel, message)`` if a message is available. If ``block`` is True, then
  it will not return until after a built-in timeout or a message arrives; if
  ``block`` is false, it will always return immediately. It is perfectly
  valid to ignore ``block`` and always return immediately, or after a delay;
  ``block`` means that the call can take as long as it likes before returning
  a message or nothing, not that it must block until it gets one.

* ``new_channel(pattern)``, a callable that takes a unicode string pattern,
  and returns a new valid channel name that does not already exist, by
  adding a unicode string after the ``!`` or ``?`` character in ``pattern``,
  and checking for existence of that name in the channel layer. The ``pattern``
  must end with ``!`` or ``?`` or this function must error. If the character
  is ``!``, making it a process-specific channel, ``new_channel`` must be
  called on the same channel layer that intends to read the channel with
  ``receive``; any other channel layer instance may not receive
  messages on this channel due to client-routing portions of the appended string.

* ``MessageTooLarge``, the exception raised when a send operation fails
  because the encoded message is over the layer's size limit.

* ``ChannelFull``, the exception raised when a send operation fails
  because the destination channel is over capacity.

* ``extensions``, a list of unicode string names indicating which
  extensions this layer provides, or an empty list if it supports none.
  The possible extensions can be seen in :ref:`asgi_extensions`.

A channel layer implementing the ``groups`` extension must also provide:

* ``group_add(group, channel)``, a callable that takes a ``channel`` and adds
  it to the group given by ``group``. Both are unicode strings. If the channel
  is already in the group, the function should return normally.

* ``group_discard(group, channel)``, a callable that removes the ``channel``
  from the ``group`` if it is in it, and does nothing otherwise.

* ``group_channels(group)``, a callable that returns an iterable which yields
  all of the group's member channel names. The return value should be serializable
  with regards to local adds and discards, but best-effort with regards to
  adds and discards on other nodes.

* ``send_group(group, message)``, a callable that takes two positional
  arguments; the group to send to, as a unicode string, and the message
  to send, as a serializable ``dict``. It may raise MessageTooLarge but cannot
  raise ChannelFull.

* ``group_expiry``, an integer number of seconds that specifies how long group
  membership is valid for after the most recent ``group_add`` call (see
  *Persistence* below)

A channel layer implementing the ``statistics`` extension must also provide:

* ``global_statistics()``, a callable that returns statistics across all channels
* ``channel_statistics(channel)``, a callable that returns statistics for specified channel

* in both cases statistics are a dict with zero or more of (unicode string keys):

  * ``messages_count``, the number of messages processed since server start
  * ``messages_count_per_second``, the number of messages processed in the last second
  * ``messages_pending``, the current number of messages waiting
  * ``messages_max_age``, how long the oldest message has been waiting, in seconds
  * ``channel_full_count``, the number of times `ChannelFull` exception has been risen since server start
  * ``channel_full_count_per_second``, the number of times `ChannelFull` exception has been risen in the last second

* Implementation may provide total counts, counts per seconds or both.


A channel layer implementing the ``flush`` extension must also provide:

* ``flush()``, a callable that resets the channel layer to a blank state,
  containing no messages and no groups (if the groups extension is
  implemented). This call must block until the system is cleared and will
  consistently look empty to any client, if the channel layer is distributed.

A channel layer implementing the ``twisted`` extension must also provide:

* ``receive_twisted(channels)``, a function that behaves
  like ``receive`` but that returns a Twisted Deferred that eventually
  returns either ``(channel, message)`` or ``(None, None)``. It is not possible
  to run it in nonblocking mode; use the normal ``receive`` for that. The
  channel layer must be able to deal with this function being called from
  many different places in a codebase simultaneously - likely once from each
  Twisted Protocol instance - and so it is recommended that implementations
  use internal connection pooling and call merging or similar.

A channel layer implementing the ``asyncio`` extension must also provide:

* ``receive_asyncio(channels)``, a function that behaves
  like ``receive`` but that fulfills the asyncio coroutine contract to
  block until either a result is available or an internal timeout is reached
  and ``(None, None)`` is returned. The channel layer must be able to deal
  with this function being called from many different places in a codebase
  simultaneously, and so it is recommended that implementations
  use internal connection pooling and call merging or similar.

Channel Semantics
-----------------

Channels **must**:

* Preserve ordering of messages perfectly with only a single reader
  and writer if the channel is a *single-reader* or *process-specific* channel.

* Never deliver a message more than once.

* Never block on message send (though they may raise ChannelFull or
  MessageTooLarge)

* Be able to handle messages of at least 1MB in size when encoded as
  JSON (the implementation may use better encoding or compression, as long
  as it meets the equivalent size)

* Have a maximum name length of at least 100 bytes.

They should attempt to preserve ordering in all cases as much as possible,
but perfect global ordering is obviously not possible in the distributed case.

They are not expected to deliver all messages, but a success rate of at least
99.99% is expected under normal circumstances. Implementations may want to
have a "resilience testing" mode where they deliberately drop more messages
than usual so developers can test their code's handling of these scenarios.


Persistence
-----------

Channel layers do not need to persist data long-term; group
memberships only need to live as long as a connection does, and messages
only as long as the message expiry time, which is usually a couple of minutes.

That said, if a channel server goes down momentarily and loses all data,
persistent socket connections will continue to transfer incoming data and
send out new generated data, but will have lost all of their group memberships
and in-flight messages.

In order to avoid a nasty set of bugs caused by these half-deleted sockets,
protocol servers should quit and hard restart if they detect that the channel
layer has gone down or lost data; shedding all existing connections and letting
clients reconnect will immediately resolve the problem.

If a channel layer implements the ``groups`` extension, it must persist group
membership until at least the time when the member channel has a message
expire due to non-consumption, after which it may drop membership at any time.
If a channel subsequently has a successful delivery, the channel layer must
then not drop group membership until another message expires on that channel.

Channel layers must also drop group membership after a configurable long timeout
after the most recent ``group_add`` call for that membership, the default being
86,400 seconds (one day). The value of this timeout is exposed as the
``group_expiry`` property on the channel layer.

Protocol servers must have a configurable timeout value for every connection-based
protocol they serve that closes the connection after the timeout, and should
default this value to the value of ``group_expiry``, if the channel
layer provides it. This allows old group memberships to be cleaned up safely,
knowing that after the group expiry the original connection must have closed,
or is about to be in the next few seconds.

It's recommended that end developers put the timeout setting much lower - on
the order of hours or minutes - to enable better protocol design and testing.
Even with ASGI's separation of protocol server restart from business logic
restart, you will likely need to move and reprovision protocol servers, and
making sure your code can cope with this is important.


.. _asgi_sub_specifications:

Message Formats
---------------

These describe the standardized message formats for the protocols this
specification supports. All messages are ``dicts`` at the top level,
and all keys are required unless explicitly marked as optional. If a key is
marked optional, a default value is specified, which is to be assumed if
the key is missing. Keys are unicode strings.

The one common key across all protocols is ``reply_channel``, a way to indicate
the client-specific channel to send responses to. Protocols are generally
encouraged to have one message type and one reply channel type to ensure ordering.

A ``reply_channel`` should be unique per connection. If the protocol in question
can have any server service a response - e.g. a theoretical SMS protocol - it
should not have ``reply_channel`` attributes on messages, but instead a separate
top-level outgoing channel.

Messages are specified here along with the channel names they are expected
on; if a channel name can vary, such as with reply channels, the varying
portion will be represented by ``!``, such as ``http.response!``, which matches
the format the ``new_channel`` callable takes.

There is no label on message types to say what they are; their type is implicit
in the channel name they are received on. Two types that are sent on the same
channel, such as HTTP responses and response chunks, are distinguished apart
by their required fields.

Message formats can be found in the sub-specifications:

.. toctree::
   :maxdepth: 1

   /asgi/www
   /asgi/delay
   /asgi/udp


Protocol Format Guidelines
--------------------------

Message formats for protocols should follow these rules, unless
a very good performance or implementation reason is present:

* ``reply_channel`` should be unique per logical connection, and not per
  logical client.

* If the protocol has server-side state, entirely encapsulate that state in
  the protocol server; do not require the message consumers to use an external
  state store.

* If the protocol has low-level negotiation, keepalive or other features,
  handle these within the protocol server and don't expose them in ASGI
  messages.

* If the protocol has guaranteed ordering and does not use a specific channel
  for a given connection (as HTTP does for body data), ASGI messages should
  include an ``order`` field (0-indexed) that preserves the ordering as
  received by the protocol server (or as sent by the client, if available).
  This ordering should span all message types emitted by the client - for
  example, a connect message might have order ``0``, and the first two frames
  order ``1`` and ``2``.

* If the protocol is datagram-based, one datagram should equal one ASGI message
  (unless size is an issue)


Approximate Global Ordering
---------------------------

While maintaining true global (across-channels) ordering of messages is
entirely unreasonable to expect of many implementations, they should strive
to prevent busy channels from overpowering quiet channels.

For example, imagine two channels, ``busy``, which spikes to 1000 messages a
second, and ``quiet``, which gets one message a second. There's a single
consumer running ``receive(['busy', 'quiet'])`` which can handle
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

In this document, and all sub-specifications, *byte string* refers to
``str`` on Python 2 and ``bytes`` on Python 3. If this type still supports
Unicode codepoints due to the underlying implementation, then any values
should be kept within the 0 - 255 range.

*Unicode string* refers to ``unicode`` on Python 2 and ``str`` on Python 3.
This document will never specify just *string* - all strings are one of the
two exact types.

Some serializers, such as ``json``, cannot differentiate between byte
strings and unicode strings; these should include logic to box one type as
the other (for example, encoding byte strings as base64 unicode strings with
a preceding special character, e.g. U+FFFF).

Channel and group names are always unicode strings, with the additional
limitation that they only use the following characters:

* ASCII letters
* The digits ``0`` through ``9``
* Hyphen ``-``
* Underscore ``_``
* Period ``.``
* Question mark ``?`` (only to delineiate single-reader channel names,
  and only one per name)
* Exclamation mark ``!`` (only to delineate process-specific channel names,
  and only one per name)



Common Questions
================

1. Why are messages ``dicts``, rather than a more advanced type?

   We want messages to be very portable, especially across process and
   machine boundaries, and so a simple encodable type seemed the best way.
   We expect frameworks to wrap each protocol-specific set of messages in
   custom classes (e.g. ``http.request`` messages become ``Request`` objects)


Copyright
=========

This document has been placed in the public domain.
