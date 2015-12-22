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

**NOTE: This is still heavily in-progress, and should not even be
considered draft yet. Even the name might change.**

Abstract
========

This document proposes a standard interface between network protocol
servers and Python applications, intended to allow handling of multiple
protocol styles (including HTTP, HTTP2, and WebSocket).

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

It also lays out new, serialisation-compatible formats for things like
HTTP requests and responses, to allow these to be transported over a
network or local socket, and thus allow separation of protocol handling
and application logic.

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
returns ``None`` or a ``(channel, message)`` tuple immediately. Integrating
this into both synchronous and asynchronous code should be easy, and it's
still possible for channel layers to use an async solution (such as
``asyncio``) if one is provided, and just provide the nonblocking call
via an in-memory queue.

The distinction between protocol servers and applications in this document
is mostly to distinguish their roles and to make illustrating concepts easier.
There is no code-level distinction between the two, and it's entirely possible
to have a process that does both, or middleware-like code that transforms
messages between two different channel layers or channel names. It is
expected, however, that most deployments will fall into this pattern.


Channels and Messages
---------------------

All communication in an ASGI stack is using messages sent over channels.
All messages must be a ``dict`` at the top level of the object, and be
serialisable by the built-in ``json`` serialiser module (though the
actual serialisation a channel layer uses is up to the implementation;
``json`` is just considered the lowest common denominator).

Channels are identified by a bytestring name consisting only of ASCII
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


Handling Protocols
------------------

ASGI messages represent two main things - internal application events
(for example, a channel might be used to queue thumbnails of previously
uploaded videos), and protocol events to/from connected clients.

As such, this specification outlines encodings to and from ASGI messages
for three common protocols (HTTP, WebSocket and raw UDP); this allows any ASGI
web server to talk to any ASGI web application, and the same for any other
protocol with a common specification. It is recommended that if other
protocols become commonplace they should gain standardised formats in a
supplementary PEP of their own.

The message formats are a key part of the specification; without them,
the protocol server and web application might be able to talk to each other,
but may not understand some of what they're saying. It's equivalent to the
standard keys in the ``environ`` dict for WSGI.

The key abstraction is that most protocols will share a few channels for
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


Groups
------

While the basic channel model is sufficient to handle basic application
needs, many more advanced uses of asynchronous messaging require
notifying many users at once when an event occurs - imagine a live blog,
for example, where every viewer should get a long poll response or
WebSocket packet when a new entry is posted.

While the concept of a *group* of channels could be 


Linearization
-------------

The design of ASGI is meant to enable a shared-nothing architecture,
where messages 


Specification Details
=====================

A *channel layer* should provide an object with XXX attributes:

* ``send(channel, message)``, a callable that takes two positional
  arguments; the channel to send on, as a byte string, and the message
  to send, as a serialisable ``dict``.

* ``receive_many(channels)``, a callable that takes a list of channel
  names as byte strings, and returns immediately with either ``None``
  or ``(channel, message)`` if a message is available.


Copyright
=========

This document has been placed in the public domain.
