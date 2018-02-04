What's new in Channels 2?
=========================

Channels 1 and Channels 2 are substantially different codebases, and the upgrade
**is a major one**. While we have attempted to keep things as familiar and
backwards-compatible as possible, major architectural shifts mean you will
need at least some code changes to upgrade.


Requirements
------------

First of all, Channels 2 is *Python 3.5 and up only*.

If you are using Python 2, or a previous version of Python 3, you cannot use
Channels 2 as it relies on the ``asyncio`` library and native Python async
support. This decision was a tough one, but ultimately Channels is a library
built around async functionality and so to not use these features would be
foolish in the long run.

Apart from that, there are no major changed requirements, and in fact Channels 2
deploys do not need separate worker and server processes and so should be easier
to manage.


Conceptual Changes
------------------

The fundamental layout and concepts of how Channels work have been significantly
changed; you'll need to understand how and why to help in upgrading.


Channel Layers and Processes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Channels 1 terminated HTTP and WebSocket connections in a separate process
to the one that ran Django code, and shuffled requests and events between them
over a cross-process *channel layer*, based on Redis or similar.

This not only meant that all request data had to be re-serialized over the
network, but that you needed to deploy and scale two separate sets of servers.
Channels 2 changes this by running the Django code in-process via a threadpool,
meaning that the network termination and application logic are combined, like
WSGI.


Application Instances
~~~~~~~~~~~~~~~~~~~~~

Because of this, all processing for a socket happens in the same process,
so ASGI applications are now instantiated once per socket and can use
local variables on ``self`` to store information, rather than the
``channel_session`` storage provided before (that is now gone entirely).

The channel layer is now only used to communicate between processes for things
like broadcast messaging - in particular, you can talk to other application
instances in direct events, rather than having to send directly to client sockets.

This means, for example, to broadcast a chat message, you would now send a
new-chat-message event to every application instance that needed it, and the application
code can handle that event, serialize the message down to the socket format,
and send it out (and apply things like multiplexing).


New Consumers
~~~~~~~~~~~~~

Because of these changes, the way consumers work has also significantly changed.
Channels 2 is now a turtles-all-the-way-down design; every aspect of the system
is designed as a valid ASGI application, including consumers and the routing
system.

The consumer base classes have changed, though if you were using the generic
consumers before, the way they work is broadly similar. However, the way that
user authentication, sessions, multiplexing, and similar features work has
changed.


Full Async
~~~~~~~~~~

Channels 2 is also built on a fundamental async foundation, and all servers
are actually running an asynchronous event loop and only jumping to synchronous
code when you interact with the Django view system or ORM. That means that
you, too, can write fully asychronous code if you wish.

It's not a requirement, but it's there if you need it. We also provide
convenience methods that let you jump between synchronous and asynchronous
worlds easily, with correct blocking semantics, so you can write most of
a consumer in an async style and then have one method that calls the Django ORM
run synchronously.


Removed Components
------------------

The binding framework has been removed entirely - it was a simplistic
implementation, and it being in the core package prevented people from exploring
their own solutions. It's likely similar concepts and APIs will appear in a
third-party (non-official-Django) package as an option for those who want them.


How to Upgrade
--------------

While this is not an exhaustive guide, here are some rough rules on how to
proceed with an upgrade.

Given the major changes to the architecture and layout of Channels 2, it is
likely that upgrading will be a significant rewrite of your code, depending on
what you are doing.

It is **not** a drop-in replacement; we would have done this if we could,
but changing to ``asyncio`` and Python 3 made it almost impossible to keep
things backwards-compatible, and we wanted to correct some major design
decisions.


Function-based consumers and Routing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Channels 1 allowed you to route by event type (e.g. ``websocket.connect``) and
pass individual functions with routing that looked like this::

    channel_routing = [
        route("websocket.connect", connect_blog, path=r'^/liveblog/(?P<slug>[^/]+)/stream/$'),
    ]

And function-based consumers that looked like this::

    def connect_blog(message, slug):
        ...

You'll need to convert these to be class-based consumers, as routing is now
done once, at connection time, and so all the event handlers have to be together
in a single ASGI application. In addition, URL arguments are no longer passed
down into the individual functions - instead, they will be provided in ``scope``
as the key ``url_route``, a dict with an ``args`` key containing a list of
positional regex groups and a ``kwargs`` key with a dict of the named groups.

Routing is also now the main entry point, so you will need to change routing
to have a ProtocolTypeRouter with URLRouters nested inside it. See
:doc:`/topics/routing` for more.


channel_session and enforce_ordering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Any use of the ``channel_session`` or ``enforce_ordering`` decorators can be
removed; ordering is now always followed as protocols are handled in the same
process, and ``channel_session`` is not needed as the same application instance
now handles all traffic from a single client.

Anywhere you stored information in the ``channel_session`` can be replaced by
storing it on ``self`` inside a consumer.


HTTP sessions and Django auth
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All :doc:`authentication </topics/authentication>` and
:doc:`sessions </topics/session>` are now done with middleware. You can remove
any decorators that handled them, like ``http_session``, ``channel_session_user``
and so on (in fact, there are no decorators in Channels 2 - it's all middleware).

To get auth now, wrap your URLRouter in an ``AuthMiddlewareStack``::

    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack

    application = ProtocolTypeRouter({
        "websocket": AuthMiddlewareStack(
            URLRouter([
                ...
            ])
        ),
    })

You need to replace accesses to ``message.http_session`` with
``self.scope["session"]``, and ``message.user`` with ``self.scope["user"]``.
There is no need to do a handoff like ``channel_session_user_from_http`` any
more - just wrap the auth middleware around and the user will be in the scope
for the lifetime of the connection.


Channel Layers
~~~~~~~~~~~~~~

Channel layers are now an optional part of Channels, and the interface they
need to provide has changed to be async. Only ``channels_redis``, formerly known as
``asgi_redis``, has been updated to match so far.

Settings are still similar to before, but there is no longer a ``ROUTING``
key (the base routing is instead defined with ``ASGI_APPLICATION``)::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("redis-server-name", 6379)],
            },
        },
    }

All consumers have a ``self.channel_layer`` and ``self.channel_name`` object
that is populated if you've configured a channel layer. Any messages you send
to the ``channel_name`` will now go to the consumer rather than directly to the
client - see the :doc:`/topics/channel_layers` documentation for more.

The method names are largely the same, but they're all now awaitables rather
than synchronous functions, and ``send_group`` is now ``group_send``.


Group objects
~~~~~~~~~~~~~

Group objects no longer exist; instead you should use the ``group_add``,
``group_discard``, and ``group_send`` methods on the ``self.channel_layer``
object inside of a consumer directly. As an example::

    class ChatConsumer(AsyncWebsocketConsumer):

        async def connect(self):
            AsyncToSync(self.channel_layer.group_add)("chat", self.channel_name)

        def disconnect(self):
            AsyncToSync(self.channel_layer.group_discard)("chat", self.channel_name)


Delay server
~~~~~~~~~~~~

If you used the delay server before to put things on hold for a few seconds,
you can now instead use an ``AsyncConsumer`` and ``asyncio.sleep``::

    class PingConsumer(AsyncConsumer):

        async def websocket_receive(self, message):
            await asyncio.sleep(1)
            await self.send({
                "type": "websocket.send",
                "text": "pong",
            })

Testing
~~~~~~~

The :doc:`testing framework </topics/testing>` has been entirely rewritten to
be async-based.

While this does make writing tests a lot easier and cleaner,
it means you must entirely rewrite any consumer tests completely - there is no
backwards-compatible interface with the old testing client as it was
synchronous. You can read more about the new testing framework in the
:doc:`testing documentation </topics/testing>`.

Also of note is that the live test case class has been renamed from
``ChannelLiveServerTestCase`` to ``ChannelsLiveServerTestCase`` - note the extra
``s``.
