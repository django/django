Channel Layers
==============

Channel layers allow you to talk between different instances of an application.
They're a useful part of making a distributed realtime application if you don't
want to have to shuttle all of your messages or events through a database.

Additionally, they can also be used in combination with a worker process
to make a basic task queue or to offload tasks - read more in
:doc:`/topics/worker`.

Channels does not ship with any channel layers you can use out of the box, as
each one depends on a different way of transporting data across a network. We
would recommend you use ``channels_redis``, which is an offical Django-maintained
layer that uses Redis as a transport and what we'll focus the examples on here.

.. note::

    Channel layers are an entirely optional part of Channels as of version 2.0.
    If you don't want to use them, just leave ``CHANNEL_LAYERS`` unset, or
    set it to the empty dict ``{}``.

.. warning::

    Channel layers have a purely async interface (for both send and receive);
    you will need to wrap them in a converter if you want to call them from
    synchronous code (see below).


Configuration
-------------

Channel layers are configured via the ``CHANNEL_LAYERS`` Django setting. It
generally looks something like this::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("redis-server-name", 6379)],
            },
        },
    }

You can get the default channel layer from a project with
``channels.layers.get_channel_layer()``, but if you are using consumers a copy
is automatically provided for you on the consumer as ``self.channel_layer``.


Synchronous Functions
---------------------

By default the ``send()``, ``group_send()``, ``group_add()`` and other functions
are async functions, meaning you have to ``await`` them. If you need to call
them from synchronous code, you'll need to use the handy
``asgiref.sync.AsyncToSync`` wrapper::

    from asgiref.sync import AsyncToSync

    AsyncToSync(channel_layer.send)("channel_name", {...})


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
and then specifying a handler method for events on it::

    class ChatConsumer(WebsocketConsumer):

        def connect(self):
            # Make a database row with our channel name
            Clients.objects.create(channel_name=self.channel_name)

        def disconnect(self):
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
we could crawl the database), and use ``channel_layer.send``::

    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    await channel_layer.send("channel_name", {
        "type": "chat.message",
        "text": "Hello there!",
    })


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
during disconnection, illustrated here on the WebSocket generic consumer::

    # This example uses WebSocket consumer, which is synchronous, and so
    # needs the async channel layer functions to be converted.
    from asgiref.sync import AsyncToSync

    class ChatConsumer(WebsocketConsumer):

        def connect(self):
            AsyncToSync(self.channel_layer.group_add)("chat", self.channel_name)

        def disconnect(self):
            AsyncToSync(self.channel_layer.group_discard)("chat", self.channel_name)

Then, to send to a group, use ``group_send``, like in this small example
which broadcasts chat messages to every connected socket when combined with
the code above::

    class ChatConsumer(WebsocketConsumer):

        ...

        def receive(self, text_data):
            AsyncToSync(self.channel_layer.group_send)(
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
should use the ``get_channel_layer`` function to retrieve it::

    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()

Then, once you have it, you can just call methods on it. Remember that
**channel layers only support async methods**, so you can either call it
from your own asynchronous context::

    for chat_name in chats:
        await channel_layer.group_send(
            chat_name,
            {"type": "chat.system_message", "text": announcement_text},
        )

Or you'll need to use AsyncToSync::

    from asgiref.sync import AsyncToSync

    AsyncToSync(channel_layer.group_send)("chat", {"type": "chat.force_disconnect")
