=======================================================
ASGI (Asynchronous Server Gateway Interface) Draft Spec
=======================================================

.. note::
  This is the second major revision of this specification, and is still in progress.


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
document), and a set of standard
:ref:`message formats for each protocol <asgi_sub_specifications>`.

Its primary goal is to provide a way to write HTTP/2 and WebSocket code,
alongside normal HTTP handling code, however, and part of this design is
ensuring there is an easy path to use both existing WSGI servers and
applications, as a large majority of Python web usage relies on WSGI and
providing an easy path forwards is critical to adoption. Details on that
interoperability are covered in :doc:`/asgi/www`.

The end result of this process has been a specification that includes generalised
inter-process communication between Python processes, with a certain set of
guarantees and delivery styles that make it suited to low-latency protocol
processing and response. It is not intended to replace things like traditional
task queues, but it is intended that it could be used for things like
distributed systems communication, or as the backbone of a service-oriented
architecure for inter-service communication.


Overview
========

ASGI consists of three different components:

- A *protocol server*, which terminates sockets and translates them into
  per-event messages
- An *application*, which lives inside a *protocol server*, is instantiated
  once per socket, and handles event messages as they happen.
- A *channel layer*, which allows communication between different application
  instances regardless of which process or machine they live in.

Like WSGI, the server hosts the application inside it, and dispatches incoming
requests to it in a standardized format. Unlike WSGI, however, applications
are instantiated objects rather than simple callables, and they can communicate
between themselves, in either a point-to-point or broadcast manner.

The inter-instance communication is an essential part of the design; Python has
several existing patterns for handling socket termination nicely with classes
(such as the Twisted protocol model), but they are limited to handling inside
a single class instance or, with some extra work, a single Python process.

ASGI frames an interface that is a bit more constrained - in that the event
messages must be network-encodeable, and follow a certain basic format - to
allow cross-process communication and thus have the same abstraction useable
from a single-connection application to a large system terminating hundreds
of thousands of sockets that are all communicating with each other.


Specification Details
=====================

Events and Messages
-------------------

ASGI decomposes protocols into a series of events that an application must
react to. For HTTP, this is as simple as two events in order - ``http.request``
and ``http.disconnect``. For something like a WebSocket, this could be a series
of different received frames.

It also lets these events be sourced from other application instances, via
either a direct message sent to the application instance's *application channel*,
or if the application subscribes its channel to a Group which gets a message
broadcast to it.

Each message is a ``dict`` with a top-level ``type`` key that contains a
unicode string of the message type. Users are free to invent their own message
types and send them between application instances for high-level events - for
example, a chat application might send chat messages with a user type of
``mychat.message``.

Because these messages are sometimes sent over a network, they need to be
serializable, and so they are only allowed to contain the following types:

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

Communication between application instances, and to other parts of a system,
is achieved via an ASGI *channel layer*. This is an abstraction that
encapsulates the idea of first-in-first-out, named channels that transport
messages over a network via what is essentially a message or service bus.

It's a specification that allows for a set of different
implementions to be swapped in based on the end-user's requirements and
infrastructure, and is fully specified in :doc:`/asgi/channel_layer.rst`.

Each application instance is assigned an *application channel* by the protocol
server when it is created, and the protocol server will listen for messages
sent to the channel and forward them to the application as event messages.

Application instances are given their application channel and the channel
layer object when they are instantiated, so they can store them and use them
later on to send messages to other application instances, Groups, or anything
else on the channel layer.


Applications
------------

ASGI applications are defined as a callable::

    application(type, reply, channel_layer, application_channel)

* ``type``: The type of protocol connecting, e.g. ``"http"`` or ``"websocket"``.
* ``reply``: A callable that takes messages and sends them down the socket
* ``channel_layer``: An ASGI :doc:`channel layer </asgi/channel_layer>`.
* ``application_channel``: Channel name that will send messages to this application instance

Which must return another callable::

    application_instance(message)

The first callable is called whenever a new socket comes in to the protocol
server, and creates a new *instance* of the application per socket (the object
that this first callable returns). That instance is then itself called each
time an event message is ready for the application - either from the connected
socket, or from another process on the channel layer - and passed the message.

This design is perhaps more easily recognised as one of its possible
implementations, as a class::

    class Application:

        def __init__(self, type, reply, channel_layer, application_channel):
            ...

        def __call__(self, message):
            ...

The application interface is defined as two callables, though, to allow more
flexibility for things like factory functions or type-based dispatchers.

Both the application instance and the ``reply`` callable passed to the instance
on instantiation take messages - these are defined in protocol specifications,
and as mentioned above, are dicts. You can use the ``type`` argument to work
out what sort of messages the application should send and receive, or indeed
to work out which type-specific Application instance to dispatch to instead.


Handling Protocols
------------------

ASGI messages represent two main things - internal application events
(for example, a channel might be used to queue thumbnails of previously
uploaded videos), and protocol events to/from connected clients.

As such, there are :ref:`sub-specifications <asgi_sub_specifications>` that
outline encodings to and from ASGI messages for common protocols like HTTP and
WebSocket; in particular, the HTTP one covers WSGI/ASGI interoperability.
It is recommended that if a protocol becomes commonplace, it should gain
standardized formats in a sub-specification of its own.

The message formats are a key part of the specification; without them,
the protocol server and application might be able to talk to each other,
but may not understand some of what the other is saying. It's equivalent to the
standard keys in the ``environ`` dict for WSGI.

Formats generally cover only the socket-based communications with a protocol
server via the application instance's callable and the ``reply`` callable, and
will come with an accompanying ``type`` value so you can work out which
protocol you are handling.


Capacity
--------

Protocol servers cannot service an unbounded number of sockets at once;
they need to be able to cap the number of simultaneous application instances.

The implementation of this is left to the individual server, but if a server
considers itself over capacity, it should close the incoming socket or request
with an appropriate error code and never even instantiate an application instance.


.. _asgi_sub_specifications:

Message Formats
---------------

These describe the standardized message formats for the protocols this
specification supports. All messages are ``dicts`` at the top level,
and all keys are required unless explicitly marked as optional. If a key is
marked optional, a default value is specified, which is to be assumed if
the key is missing. Keys are unicode strings.

The one common key across all protocols is ``type``, a way to indicate
what type of message is being sent. The ``type`` should be namespaced as
``protocol.message_type``, where the ``protocol`` is the value of ``type``
given to a new application instance (e.g. ``http``), and ``message_type`` is
defined by the protocol spec. Examples of a ``type`` value include
``http.request`` and ``websocket.send``.

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

* If the protocol has low-level negotiation, keepalive or other features,
  handle these within the protocol server and don't expose them in ASGI
  messages.

* If the protocol is datagram-based, one datagram should equal one ASGI message
  (unless size is an issue)


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
