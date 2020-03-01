Channel Layers
==============

Channel layers allow you to talk between different instances of an application.
They're a useful part of making a distributed realtime application if you don't
want to have to shuttle all of your messages or events through a database.

Additionally, they can also be used in combination with a worker process
to make a basic task queue or to offload tasks - read more in
:doc:`/topics/worker`.


.. note::

    Channel layers are an entirely optional part of Channels as of version 2.0.
    If you don't want to use them, just leave ``CHANNEL_LAYERS`` unset, or
    set it to the empty dict ``{}``.

    Messages across channel layers also go to consumers/ASGI application
    instances, just like events from the client, and so they now need a
    ``type`` key as well. See more below.


.. warning::

    Channel layers have a purely async interface (for both send and receive);
    you will need to wrap them in a converter if you want to call them from
    synchronous code (see below).


Configuration
-------------

Channel layers are configured via the ``CHANNEL_LAYERS`` Django setting.

You can get the default channel layer from a project with
``channels.layers.get_channel_layer()``, but if you are using consumers a copy
is automatically provided for you on the consumer as ``self.channel_layer``.

Redis Channel Layer
**********************

`channels_redis`_ is the only official Django-maintained channel layer
supported for production use. The layer uses Redis as its backing store,
and supports both a single-server and sharded configurations, as well as
group support. To use this layer you'll need to install the `channels_redis`_
package.

.. _`channels_redis`: https://pypi.org/project/channels-redis/

In this example, Redis is running on localhost (127.0.0.1) port 6379:

.. code-block:: python

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("127.0.0.1", 6379)],
            },
        },
    }

In-Memory Channel Layer
**********************

.. warning::

    **Not for Production Use.** In-memory channel layers operate each
    process as a separate layer, which means no cross-process
    messaging is possible. As the core value of channel layers
    to provide distributed messaging, in-memory usage will
    result in sub-optimal performance and data-loss in a
    multi-instance environment.

Channels also comes packaged with an in-memory Channels Layer. This layer can
be helpful in for :doc:`/topics/testing` or local-development purposes:

.. code-block:: python

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }

Synchronous Functions
---------------------

By default the ``send()``, ``group_send()``, ``group_add()`` and other functions
are async functions, meaning you have to ``await`` them. If you need to call
them from synchronous code, you'll need to use the handy
``asgiref.sync.async_to_sync`` wrapper:

.. code-block:: python

    from asgiref.sync import async_to_sync

    async_to_sync(channel_layer.send)("channel_name", {...})


What To Send Over The Channel Layer
-----------------------------------

Unlike in Channels 1, the channel layer is only for high-level
application-to-application communication. When you send a message, it is
received by the consumers listening to the group or channel on the other end,
and not transported to that consumer's socket directly.

What this means is that you should send high-level events over the channel
layer, and then have consumers handle those events and do appropriate low-level
networking to their attached client.

For example, the `multichat example <https://github.com/andrewgodwin/channels-examples/tree/master/multichat>`_
in Andrew Godwin's ``channels-examples`` repository sends events like this
over the channel layer:

.. code-block:: python

    await self.channel_layer.group_send(
        room.group_name,
        {
            "type": "chat.message",
            "room_id": room_id,
            "username": self.scope["user"].username,
            "message": message,
        }
    )

And then the consumers define a handling function to receive those events
and turn them into WebSocket frames:

.. code-block:: python

    async def chat_message(self, event):
        """
        Called when someone has messaged our chat.
        """
        # Send a message down to the client
        await self.send_json(
            {
                "msg_type": settings.MSG_TYPE_MESSAGE,
                "room": event["room_id"],
                "username": event["username"],
                "message": event["message"],
            },
        )

Any consumer based on Channels' ``SyncConsumer`` or ``AsyncConsumer`` will
automatically provide you a ``self.channel_layer`` and ``self.channel_name``
attribute, which contains a pointer to the channel layer instance and the
channel name that will reach the consumer respectively.

Any message sent to that channel name - or to a group the channel name was
added to - will be received by the consumer much like an event from its
connected client, and dispatched to a named method on the consumer. The name
of the method will be the ``type`` of the event with periods replaced by
underscores - so, for example, an event coming in over the channel layer
with a ``type`` of ``chat.join`` will be handled by the method ``chat_join``.

.. note::

    If you are inheriting from the ``AsyncConsumer`` class tree, all your
    event handlers, including ones for events over the channel layer, must
    be asynchronous (``async def``). If you are in the ``SyncConsumer`` class
    tree instead, they must all be synchronous (``def``).


Single Channels
---------------

Each application instance - so, for example, each long-running HTTP request
or open WebSocket - results in a single Consumer instance, and if you have
channel layers enabled, Consumers will generate a unique *channel name* for
themselves, and start listening on it for events.

This means you can send those consumers events from outside the process -
from other consumers, maybe, or from management commands - and they will react
to them and run code just like they would events from their client connection.

The channel name is available on a consumer as ``self.channel_name``. Here's
an example of writing the channel name into a database upon connection,
and then specifying a handler method for events on it:

.. code-block:: python

    class ChatConsumer(WebsocketConsumer):

        def connect(self):
            # Make a database row with our channel name
            Clients.objects.create(channel_name=self.channel_name)

        def disconnect(self, close_code):
            # Note that in some rare cases (power loss, etc) disconnect may fail
            # to run; this naive example would leave zombie channel names around.
            Clients.objects.filter(channel_name=self.channel_name).delete()

        def chat_message(self, event):
            # Handles the "chat.message" event when it's sent to us.
            self.send(text_data=event["text"])

Note that, because you're mixing event handling from the channel layer and
from the protocol connection, you need to make sure that your type names do not
clash. It's recommended you prefix type names (like we did here with ``chat.``)
to avoid clashes.

To send to a single channel, just find its channel name (for the example above,
we could crawl the database), and use ``channel_layer.send``:

.. code-block:: python

    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.send("channel_name", {
        "type": "chat.message",
        "text": "Hello there!",
    })


.. _groups:

Groups
------

Obviously, sending to individual channels isn't particularly useful - in most
cases you'll want to send to multiple channels/consumers at once as a broadcast.
Not only for cases like a chat where you want to send incoming messages to
everyone in the room, but even for sending to an individual user who might have
more than one browser tab or device connected.

You can construct your own solution for this if you like, using your existing
datastores, or use the Groups system built-in to some channel layers. Groups
are a broadcast system that:

* Allows you to add and remove channel names from named groups, and send to
  those named groups.

* Provides group expiry for clean-up of connections whose disconnect handler
  didn't get to run (e.g. power failure)

They do not allow you to enumerate or list the channels in a group; it's a
pure broadcast system. If you need more precise control or need to know who
is connected, you should build your own system or use a suitable third-party
one.

You use groups by adding a channel to them during connection, and removing it
during disconnection, illustrated here on the WebSocket generic consumer:

.. code-block:: python

    # This example uses WebSocket consumer, which is synchronous, and so
    # needs the async channel layer functions to be converted.
    from asgiref.sync import async_to_sync

    class ChatConsumer(WebsocketConsumer):

        def connect(self):
            async_to_sync(self.channel_layer.group_add)("chat", self.channel_name)

        def disconnect(self, close_code):
            async_to_sync(self.channel_layer.group_discard)("chat", self.channel_name)

Then, to send to a group, use ``group_send``, like in this small example
which broadcasts chat messages to every connected socket when combined with
the code above:

.. code-block:: python

    class ChatConsumer(WebsocketConsumer):

        ...

        def receive(self, text_data):
            async_to_sync(self.channel_layer.group_send)(
                "chat",
                {
                    "type": "chat.message",
                    "text": text_data,
                },
            )

        def chat_message(self, event):
            self.send(text_data=event["text"])


Using Outside Of Consumers
--------------------------

You'll often want to send to the channel layer from outside of the scope of
a consumer, and so you won't have ``self.channel_layer``. In this case, you
should use the ``get_channel_layer`` function to retrieve it:

.. code-block:: python

    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()

Then, once you have it, you can just call methods on it. Remember that
**channel layers only support async methods**, so you can either call it
from your own asynchronous context:

.. code-block:: python

    for chat_name in chats:
        await channel_layer.group_send(
            chat_name,
            {"type": "chat.system_message", "text": announcement_text},
        )

Or you'll need to use async_to_sync:

.. code-block:: python

    from asgiref.sync import async_to_sync

    async_to_sync(channel_layer.group_send)("chat", {"type": "chat.force_disconnect"})
