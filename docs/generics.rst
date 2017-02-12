Generic Consumers
=================

Much like Django's class-based views, Channels has class-based consumers.
They provide a way for you to arrange code so it's highly modifiable and
inheritable, at the slight cost of it being harder to figure out the execution
path.

We recommend you use them if you find them valuable; normal function-based
consumers are also entirely valid, however, and may result in more readable
code for simpler tasks.

There is one base generic consumer class, ``BaseConsumer``, that provides
the pattern for method dispatch and is the thing you can build entirely
custom consumers on top of, and then protocol-specific subclasses that provide
extra utility - for example, the ``WebsocketConsumer`` provides automatic
group management for the connection.

When you use class-based consumers in :doc:`routing <routing>`, you need
to use ``route_class`` rather than ``route``; ``route_class`` knows how to
talk to the class-based consumer and extract the list of channels it needs
to listen on from it directly, rather than making you pass it in explicitly.

Here's a routing example::

    from channels import route, route_class

    channel_routing = [
        route_class(consumers.ChatServer, path=r"^/chat/"),
        route("websocket.connect", consumers.ws_connect, path=r"^/$"),
    ]

Class-based consumers are instantiated once for each message they consume,
so it's safe to store things on ``self`` (in fact, ``self.message`` is the
current message by default, and ``self.kwargs`` are the keyword arguments
passed in from the routing).

Base
----

The ``BaseConsumer`` class is the foundation of class-based consumers, and what
you can inherit from if you wish to build your own entirely from scratch.

You use it like this::

    from channels.generic import BaseConsumer

    class MyConsumer(BaseConsumer):

        method_mapping = {
            "channel.name.here": "method_name",
        }

        def method_name(self, message, **kwargs):
            pass

All you need to define is the ``method_mapping`` dictionary, which maps
channel names to method names. The base code will take care of the dispatching
for you, and set ``self.message`` to the current message as well.

If you want to perfom more complicated routing, you'll need to override the
``dispatch()`` and ``channel_names()`` methods in order to do the right thing;
remember, though, your channel names cannot change during runtime and must
always be the same for as long as your process runs.

``BaseConsumer`` and all other generic consumers that inherit from it provide
two instance variables on the class:

* ``self.message``, the :ref:`Message object <ref-message>` representing the
  message the consumer was called for.
* ``self.kwargs``, keyword arguments from the :doc:`routing`


WebSockets
----------

There are two WebSockets generic consumers; one that provides group management,
simpler send/receive methods, and basic method routing, and a subclass which
additionally automatically serializes all messages sent and receives using JSON.

The basic WebSocket generic consumer is used like this::

    from channels.generic.websockets import WebsocketConsumer

    class MyConsumer(WebsocketConsumer):

        # Set to True to automatically port users from HTTP cookies
        # (you don't need channel_session_user, this implies it)
        http_user = True

        # Set to True if you want it, else leave it out
        strict_ordering = False

        def connection_groups(self, **kwargs):
            """
            Called to return the list of groups to automatically add/remove
            this connection to/from.
            """
            return ["test"]

        def connect(self, message, **kwargs):
            """
            Perform things on connection start
            """
            # Accept the connection; this is done by default if you don't override
            # the connect function.
            self.message.reply_channel.send({"accept": True})

        def receive(self, text=None, bytes=None, **kwargs):
            """
            Called when a message is received with either text or bytes
            filled out.
            """
            # Simple echo
            self.send(text=text, bytes=bytes)

        def disconnect(self, message, **kwargs):
            """
            Perform things on connection close
            """
            pass

You can call ``self.send`` inside the class to send things to the connection's
``reply_channel`` automatically. Any group names returned from ``connection_groups``
are used to add the socket to when it connects and to remove it from when it
disconnects; you get keyword arguments too if your URL path, say, affects
which group to talk to.

Additionally, the property ``self.path`` is always set to the current URL path.

The JSON-enabled consumer looks slightly different::

    from channels.generic.websockets import JsonWebsocketConsumer

    class MyConsumer(JsonWebsocketConsumer):

        # Set to True if you want it, else leave it out
        strict_ordering = False

        def connection_groups(self, **kwargs):
            """
            Called to return the list of groups to automatically add/remove
            this connection to/from.
            """
            return ["test"]

        def connect(self, message, **kwargs):
            """
            Perform things on connection start
            """
            pass

        def receive(self, content, **kwargs):
            """
            Called when a message is received with decoded JSON content
            """
            # Simple echo
            self.send(content)

        def disconnect(self, message, **kwargs):
            """
            Perform things on connection close
            """
            pass

For this subclass, ``receive`` only gets a ``content`` argument that is the
already-decoded JSON as Python datastructures; similarly, ``send`` now only
takes a single argument, which it JSON-encodes before sending down to the
client.

Note that this subclass still can't intercept ``Group.send()`` calls to make
them into JSON automatically, but it does provide ``self.group_send(name, content)``
that will do this for you if you call it explicitly.

``self.close()`` is also provided to easily close the WebSocket from the
server end with an optional status code once you are done with it.

.. _multiplexing:

WebSocket Multiplexing
----------------------

Channels provides a standard way to multiplex different data streams over
a single WebSocket, called a ``Demultiplexer``.

It expects JSON-formatted WebSocket frames with two keys, ``stream`` and
``payload``, and will match the ``stream`` against the mapping to find a
channel name. It will then forward the message onto that channel while
preserving ``reply_channel``, so you can hook consumers up to them directly
in the ``routing.py`` file, and use authentication decorators as you wish.


Example using class-based consumer::

    from channels.generic.websockets import WebsocketDemultiplexer, JsonWebsocketConsumer

    class EchoConsumer(JsonWebsocketConsumer):
        def connect(self, message, multiplexer, **kwargs):
            # Send data with the multiplexer
            multiplexer.send({"status": "I just connected!"})

        def disconnect(self, message, multiplexer, **kwargs):
            print("Stream %s is closed" % multiplexer.stream)

        def receive(self, content, multiplexer, **kwargs):
            # Simple echo
            multiplexer.send({"original_message": content})


    class AnotherConsumer(JsonWebsocketConsumer):
        def receive(self, content, multiplexer=None, **kwargs):
            # Some other actions here
            pass


    class Demultiplexer(WebsocketDemultiplexer):

        # Wire your JSON consumers here: {stream_name : consumer}
        consumers = {
            "echo": EchoConsumer,
            "other": AnotherConsumer,
        }


The ``multiplexer`` allows the consumer class to be independant of the stream name.
It holds the stream name and the demultiplexer on the attributes ``stream`` and ``demultiplexer``.

The :doc:`data binding <binding>` code will also send out messages to clients
in the same format, and you can encode things in this format yourself by
using the ``WebsocketDemultiplexer.encode`` class method.


Sessions and Users
------------------

If you wish to use ``channel_session`` or ``channel_session_user`` with a
class-based consumer, simply set one of the variables in the class body::

    class MyConsumer(WebsocketConsumer):

        channel_session_user = True

This will run the appropriate decorator around your handler methods, and provide
``message.channel_session`` and ``message.user`` on the message object - both
the one passed in to your handler as an argument as well as ``self.message``,
as they point to the same instance.

And if you just want to use the user from the django session, add ``http_user``::

    class MyConsumer(WebsocketConsumer):

        http_user = True

This will give you ``message.user``, which will be the same as ``request.user``
would be on a regular View.


Applying Decorators
-------------------

To apply decorators to a class-based consumer, you'll have to wrap a functional
part of the consumer; in this case, ``get_handler`` is likely the place you
want to override; like so::

    class MyConsumer(WebsocketConsumer):

        def get_handler(self, *args, **kwargs):
            handler = super(MyConsumer, self).get_handler(*args, **kwargs)
            return your_decorator(handler)

You can also use the Django ``method_decorator`` utility to wrap methods that
have ``message`` as their first positional argument - note that it won't work
for more high-level methods, like ``WebsocketConsumer.receive``.


As route
--------

Instead of making routes using ``route_class`` you may use the ``as_route`` shortcut.
This function takes route filters (:ref:`filters`) as kwargs and returns
``route_class``. For example::

    from . import consumers

    channel_routing = [
        consumers.ChatServer.as_route(path=r"^/chat/"),
    ]

Use the ``attrs`` dict keyword for dynamic class attributes. For example you have
the generic consumer::

    class MyGenericConsumer(WebsocketConsumer):
        group = 'default'
        group_prefix = ''

        def connection_groups(self, **kwargs):
            return ['_'.join(self.group_prefix, self.group)]

You can create consumers with different ``group`` and  ``group_prefix`` with ``attrs``,
like so::

    from . import consumers

    channel_routing = [
        consumers.MyGenericConsumer.as_route(path=r"^/path/1/",
                                             attrs={'group': 'one', 'group_prefix': 'pre'}),
        consumers.MyGenericConsumer.as_route(path=r"^/path/2/",
                                             attrs={'group': 'two', 'group_prefix': 'public'}),
    ]

