===========================
Channel Layer Specification
===========================

.. note::

    Channel layers are now internal only to Channels, and not used as part of
    ASGI. This spec defines what Channels and applications written using it
    expect a channel layer to provide.

Abstract
========

This document outlines a set of standardized definitions for *channels* and
a *channel layer* which provides a mechanism to send and receive messages over
them. They allow inter-process communication between different processes to
help build applications that have messaging and events between different clients.


Overview
========

Messages
--------

Messages must be a ``dict``. Because these messages are sometimes sent
over a network, they need to be serializable, and so they are only allowed
to contain the following types:

* Byte strings
* Unicode strings
* Integers (within the signed 64 bit range)
* Floating point numbers (within the IEEE 754 double precision range)
* Lists (tuples should be encoded as lists)
* Dicts (keys must be unicode strings)
* Booleans
* None

Channels
--------

Channels are identified by a unicode string name consisting only of ASCII
letters, ASCII numerical digits, periods (``.``), dashes (``-``) and
underscores (``_``), plus an optional type character (see below).

Channels are a first-in, first out queue with at-most-once delivery
semantics. They can have multiple writers and multiple readers; only a single
reader should get each written message. Implementations must never deliver
a message more than once or to more than one reader, and must drop messages if
this is necessary to achieve this restriction.

In order to aid with scaling and network architecture, a distinction
is made between channels that have multiple readers and
*process-specific channels* that are read from a single known process.

*Normal channel* names contain no type characters, and can be routed however
the backend wishes; in particular, they do not have to appear globally
consistent, and backends may shard their contents out to different servers
so that a querying client only sees some portion of the messages. Calling
``receive`` on these channels does not guarantee that you will get the
messages in order or that you will get anything if the channel is non-empty.

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
channel layer and the way it is deployed, and it is recommended that users
are allowed to configure the expiry time.

The maximum message size is 1MB if the message were encoded as JSON;
if more data than this needs to be transmitted it must be chunked into
smaller messages. All channel layers must support messages up
to this size, but channel layer users are encouraged to keep well below it.


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

There is potential to add further extensions; these may be defined by
a separate specification, or a new version of this specification.

If application code requires an extension, it should check for it as soon
as possible, and hard error if it is not provided. Frameworks should
encourage optional use of extensions, while attempting to move any
extension-not-found errors to process startup rather than message handling.


Asynchronous Support
--------------------

All channel layers must provide asynchronous (coroutine) methods for their
primary endpoints. End-users will be able to achieve synchronous versions
using the ``asgiref.sync.async_to_sync`` wrapper.


Groups
------

While the basic channel model is sufficient to handle basic application
needs, many more advanced uses of asynchronous messaging require
notifying many users at once when an event occurs - imagine a live blog,
for example, where every viewer should get a long poll response or
WebSocket packet when a new entry is posted.

Thus, there is an *optional* groups extension which allows easier broadcast
messaging to groups of channels. End-users are free, of course, to use just
channel names and direct sending and build their own persistence/broadcast
system instead.


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

Process-local channels must apply their capacity on the non-local part (that is,
up to and including the ``!`` character), and so capacity is shared among all
of the "virtual" channels inside it.

Sending to a group never raises ChannelFull; instead, it must silently drop
the message if it is over capacity, as per ASGI's at-most-once delivery
policy.


Specification Details
=====================

A *channel layer* must provide an object with these attributes
(all function arguments are positional):

* ``coroutine send(channel, message)``, that takes two arguments: the
  channel to send on, as a unicode string, and the message
  to send, as a serializable ``dict``.

* ``coroutine receive(channel)``, that takes a single channel name and returns
  the next received message on that channel.

* ``coroutine new_channel()``, which returns a new process-specific channel
  that can be used to give to a local coroutine or receiver.

* ``MessageTooLarge``, the exception raised when a send operation fails
  because the encoded message is over the layer's size limit.

* ``ChannelFull``, the exception raised when a send operation fails
  because the destination channel is over capacity.

* ``extensions``, a list of unicode string names indicating which
  extensions this layer provides, or an empty list if it supports none.
  The possible extensions can be seen in :ref:`asgi_extensions`.

A channel layer implementing the ``groups`` extension must also provide:

* ``coroutine group_add(group, channel)``, that takes a ``channel`` and adds
  it to the group given by ``group``. Both are unicode strings. If the channel
  is already in the group, the function should return normally.

* ``coroutine group_discard(group, channel)``, that removes the ``channel``
  from the ``group`` if it is in it, and does nothing otherwise.

* ``coroutine group_send(group, message)``, that takes two positional
  arguments; the group to send to, as a unicode string, and the message
  to send, as a serializable ``dict``. It may raise MessageTooLarge but cannot
  raise ChannelFull.

* ``group_expiry``, an integer number of seconds that specifies how long group
  membership is valid for after the most recent ``group_add`` call (see
  *Persistence* below)

A channel layer implementing the ``flush`` extension must also provide:

* ``coroutine flush()``, that resets the channel layer to a blank state,
  containing no messages and no groups (if the groups extension is
  implemented). This call must block until the system is cleared and will
  consistently look empty to any client, if the channel layer is distributed.


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

If a channel layer implements the ``groups`` extension, it must persist group
membership until at least the time when the member channel has a message
expire due to non-consumption, after which it may drop membership at any time.
If a channel subsequently has a successful delivery, the channel layer must
then not drop group membership until another message expires on that channel.

Channel layers must also drop group membership after a configurable long timeout
after the most recent ``group_add`` call for that membership, the default being
86,400 seconds (one day). The value of this timeout is exposed as the
``group_expiry`` property on the channel layer.


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


Copyright
=========

This document has been placed in the public domain.
