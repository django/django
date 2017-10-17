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


Overview
========

ASGI consists of two different components:

- A *protocol server*, which terminates sockets and translates them into
  per-event messages

- An *application*, which lives inside a *protocol server*, is instantiated
  once per socket, and handles event messages as they happen.

Like WSGI, the server hosts the application inside it, and dispatches incoming
requests to it in a standardized format. Unlike WSGI, however, applications
are instantiated objects rather than simple callables, and must run as
coroutines (on the main thread; they are free to use threading or other processes
if they need synchronous code).

Unlike WSGI, there are two separate parts to an ASGI connection:

- A *connection scope*, which represents a connection to a user and
  survives until the user's connection closes.

- *Events*, which are sent to the application as things happen on the
  connection.

Applications are instantiated with a connection scope, and then run in an
event loop where they are expected to handle events and send data back to the
client.


Specification Details
=====================

Connection Scope
----------------

Every connection by a user to an ASGI application results in an instance of
that application being created for the connection. How long this lives, and
what information it gets given upon creation, is called the *connection scope*.

For example, under HTTP the connection scope lasts just one request, but it
contains most of the request data (apart from the HTTP request body).

Under WebSocket, though, this connection scope lasts for as long as the socket
is connected. The scope contains information like the WebSocket's path, but
details like incoming messages come through as Events instead.

Some protocols may give you a connection scope with very limited information up
front because they encapsulate something like a handshake. Each protocol
definition must contain information about how long its connection scope lasts,
and what information you will get inside it.

Applications **cannot** communicate with the client when they are
initialized and given their connection scope; they must wait until an event
comes in and react to that.


Events and Messages
-------------------

ASGI decomposes protocols into a series of events that an application must
react to. For HTTP, this is as simple as two events in order - ``http.request``
and ``http.disconnect``. For something like a WebSocket, it could be more like
``websocket.connect``, ``websocket.receive``, ``websocket.receive``,
``websocket.disconnect``.

Each message is a ``dict`` with a top-level ``type`` key that contains a
unicode string of the message type. Users are free to invent their own message
types and send them between application instances for high-level events - for
example, a chat application might send chat messages with a user type of
``mychat.message``. It is expected that applications would be able to handle
a mixed set of events, some sourced from the incoming client connection and
some from other parts of the application.

Because these messages could be sent over a network, they need to be
serializable, and so they are only allowed to contain the following types:

* Byte strings
* Unicode strings
* Integers (within the signed 64 bit range)
* Floating point numbers (within the IEEE 754 double precision range)
* Lists (tuples should be encoded as lists)
* Dicts (keys must be unicode strings)
* Booleans
* None


Applications
------------

ASGI applications are defined as a callable::

    application(scope)

* ``scope``: The Connection Scope, a disctionary that contains at least a
  ``type`` key specifying the protocol that is incoming.

Which must return another, awaitable callable::

    coroutine application_instance(receive, send)

The first callable is called whenever a new socket comes in to the protocol
server, and creates a new *instance* of the application per socket (the
instance is the object that this first callable returns).

That instance is then called with a pair of awaitables:

* ``receive``, an awaitable that will yield a new Event when one is available
* ``send``, an awaitable that will return once the send has been completed

This design is perhaps more easily recognised as one of its possible
implementations, as a class::

    class Application:

        def __init__(self, scope):
            ...

        async def __call__(self, send, receive):
            ...

The application interface is specified as the more generic case of two callables
to allow more flexibility for things like factory functions or type-based
dispatchers.

Both the ``scope`` and the format of the messages you send and receive are
defined by one of the application protocols. The key ``scope["type"]`` will
always be present, and can be used to work out which protocol is incoming.

The :ref:`sub-specifications <asgi_sub_specifications>` cover these scope
and message formats. They are equivalent to the specification for keys in the
``environ`` dict for WSGI.


.. _asgi_sub_specifications:

Protocol Specfications
----------------------

These describe the standardized scope and message formats for various protocols.

The one common key across all scopes and messages is ``type``, a way to indicate
what type of scope or message is being received.

In scopes, the ``type`` key should be a simple string, like ``"http"`` or
``"websocket"``, as defined in the specification.

In messages, the ``type`` should be namespaced as ``protocol.message_type``,
where the ``protocol`` matches the scope type, and ``message_type`` is
defined by the protocol spec. Examples of a message ``type`` value include
``http.request`` and ``websocket.send``.

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
  events. You want to try and complete negotiation and present the application
  with rich information in its connection scope.

* If the protocol is datagram-based, one datagram should equal one ASGI message
  (unless size is an issue)


Strings and Unicode
-------------------

In this document, and all sub-specifications, *byte string* refers to
the ``bytes`` type in Python 3. *Unicode string* refers to the ``str`` type
in Python 3.

This document will never specify just *string* - all strings are one of the
two exact types.

Some serializers, such as ``json``, cannot differentiate between byte
strings and unicode strings; these should include logic to box one type as
the other (for example, encoding byte strings as base64 unicode strings with
a preceding special character, e.g. U+FFFF), so the distinction is always
preserved even across the network.


Copyright
=========

This document has been placed in the public domain.
