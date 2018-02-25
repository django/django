Introduction
============

Welcome to Channels! Channels changes Django to weave asynchronous code
underneath and through Django's synchronous core, allowing Django projects
to handle not only HTTP, but protocols that require long-running connections
too - WebSockets, MQTT, chatbots, amateur radio, and more.

It does this while preserving Django's synchronous and easy-to-use nature,
allowing you to choose how your write your code - synchronous in a style like
Django views, fully asynchronous, or a mixture of both. On top of this, it
provides integrations with Django's auth system, session system, and more,
making it easier than ever to extend your HTTP-only project to other protocols.

It also bundles this event-driven architecture with *channel layers*,
a system that allows you to easily communicate between processes, and separate
your project into different processes.

If you haven't yet installed Channels, you may want to read :doc:`installation`
first to get it installed. This introduction isn't a direct tutorial, but
you should be able to use it to follow along and make changes to an existing
Django project if you like.


Turtles All The Way Down
------------------------

Channels operates on the principle of "turtles all the way down" - we have
a single idea of what a channels "application" is, and even the simplest of
*consumers* (the equivalent of Django views) are an entirely valid
:doc:`/asgi` application you can run by themselves.

.. note::
    ASGI is the name for the asynchronous server specification that Channels
    is built on. Like WSGI, it is designed to let you choose between different
    servers and frameworks rather than being locked into Channels and our server
    Daphne.

Channels gives you the tools to write these basic *consumers* - individual
pieces that might handle chat messaging, or notifications - and tie them
together with URL routing, protocol detection and other handy things to
make a full application.

We treat HTTP and the existing Django views as parts of a bigger whole.
Traditional Django views are still there with Channels and still useable -
we wrap them up in an ASGI application called ``channels.http.AsgiHandler`` -
but you can now also write custom HTTP long-polling handling, or WebSocket
receivers, and have that code sit alongside your existing code. URL routing,
middleware - they are all just ASGI applications.

Our belief is that you want the ability to use safe, synchronous techniques
like Django views for most code, but have the option to drop down to a more
direct, asynchronous interface for complex tasks.


Scopes and Events
------------------

Channels splits up incoming connections into two components: a *scope*,
and a series of *events*.

The *scope* is a set of details about a single incoming connection - such as
the path a web request was made from, or the originating IP address of a
WebSocket, or the user messaging a chatbot - and persists throughout the
connection.

For HTTP, the scope just lasts a single request. For WebSocket, it lasts for
the lifetime of the socket (but changes if the socket closes and reconnects).
For other protocols, it varies based on how the protocol's ASGI spec is written;
for example, it's likely that a chatbot protocol would keep one scope open
for the entirety of a user's conversation with the bot, even if the underlying
chat protocol is stateless.

During the lifetime of this *scope*, a series of *events* occur. These
represent user interactions - making a HTTP request, for example, or
sending a WebSocket frame. Your Channels or ASGI applications will be
**instantiated once per scope**, and then be fed the stream of *events*
happening within that scope to decide what to do with.

An example with HTTP:

* The user makes a HTTP request.
* We open up a new ``http`` type scope with details of the request's path,
  method, headers, etc.
* We send a ``http.request`` event with the HTTP body content
* The Channels or ASGI application processes this and generates a
  ``http.response`` event to send back to the browser and close the connection.
* The HTTP request/response is completed and the scope is destroyed.

An example with a chatbot:

* The user sends a first message to the chatbot.
* This opens a scope containing the user's username, chosen name, and user ID.
* The application is given a ``chat.received_message`` event with the event text.
  It does not have to respond, but could send one, two or more other chat messages
  back as ``chat.send_message`` events if it wanted to.
* The user sends more messages to the chatbot and more ``chat.received_message``
  events are generated.
* After a timeout or when the application process is restarted the scope is
  closed.

Within the lifetime of a scope - be that a chat, a HTTP request, a socket
connection or something else - you will have one application instance handling
all the events from it, and you can persist things onto the application
instance as well. You can choose to write a raw ASGI application if you wish,
but Channels gives you an easy-to-use abstraction over them called *consumers*.


What is a Consumer?
-------------------

A consumer is the basic unit of Channels code. We call it a *consumer* as it
*consumes events*, but you can think of it as its own tiny little application.
When a request or new socket comes in, Channels will follow its routing table -
we'll look at that in a bit - find the right consumer for that incoming
connection, and start up a copy of it.

This means that, unlike Django views, consumers are long-running. They can
also be short-running - after all, HTTP requests can also be served by consumers -
but they're built around the idea of living for a little while (they live for
the duration of a *scope*, as we described above).

A basic consumer looks like this::

    class ChatConsumer(WebsocketConsumer):

        def connect(self):
            self.username = "Anonymous"
            self.accept()
            self.send(text_data="[Welcome %s!]" % self.username)

        def receive(self, *, text_data):
            if text.startswith("/name"):
                self.username = text[5:].strip()
                self.send(text_data="[set your username to %s]" % self.username)
            else:
                self.send(text_data=self.username + ": " + text)

        def disconnect(self, message):
            pass

Each different protocol has different kinds of events that happen, and
each type is represented by a different method. You write code that handles
each event, and Channels will take care of scheduling them and running them
all in parallel.

Underneath, Channels is running on a fully asynchronous event loop, and
if you write code like above, it will get called in a synchronous thread.
This means you can safely do blocking operations, like calling the Django ORM::

    class LogConsumer(WebsocketConsumer):

        def connect(self, message):
            Log.objects.create(
                type="connected",
                client=self.scope["client"],
            )

However, if you want more control and you're willing to work only in
asynchronous functions, you can write fully asynchronous consumers::

    class PingConsumer(AsyncConsumer):
        async def websocket_connect(self, message):
            await self.send({
                "type": "websocket.accept",
            })

        async def websocket_receive(self, message):
            await asyncio.sleep(1)
            await self.send({
                "type": "websocket.send",
                "text": "pong",
            })

You can read more about consumers in :doc:`/topics/consumers`.


Routing and Multiple Protocols
------------------------------

You can combine multiple Consumers (which are, remember, their own ASGI apps)
into one bigger app that represents your project using routing::

    application = URLRouter([
        url("^chat/admin/$", AdminChatConsumer),
        url("^chat/$", PublicChatConsumer),
    ])

Channels is not just built around the world of HTTP and WebSockets - it also
allows you to build any protocol into a Django environment, by building a
server that maps those protocols into a similar set of events. For example,
you can build a chatbot in a similar style::

    class ChattyBotConsumer(SyncConsumer):

        def telegram_message(self, message):
            """
            Simple echo handler for telegram messages in any chat.
            """
            self.send({
                "type": "telegram.message",
                "text": "You said: %s" % message["text"],
            })

And then use another router to have the one project able to serve both
WebSockets and chat requests::

    application = ProtocolTypeRouter({

        "websocket": URLRouter([
            url("^chat/admin/$", AdminChatConsumer),
            url("^chat/$", PublicChatConsumer),
        ]),

        "telegram": ChattyBotConsumer,
    })

The goal of Channels is to let you build out your Django projects to work
across any protocol or transport you might encounter in the modern web, while
letting you work with the familiar components and coding style you're used to.

For more information about protocol routing, see :doc:`/topics/routing`.


Cross-Process Communication
---------------------------

Much like a standard WSGI server, your application code that is handling
protocol events runs inside the server process itself - for example, WebSocket
handling code runs inside your WebSocket server process.

Each socket or connection to your overall application is handled by a
*application instance* inside one of these servers. They get called and can
send data back to the client directly.

However, as you build more complex application systems you start needing to
communicate between different *application instances* - for example, if you
are building a chatroom, when one *application instance* receives an incoming
message, it needs to distribute it out to any other instances that represent
people in the chatroom.

You can do this by polling a database, but Channels introduces the idea of
a *channel layer*, a low-level abstraction around a set of transports that
allow you to send information between different processes. Each application
instance has a unique *channel name*, and can join *groups*, allowing both
point-to-point and broadcast messaging.

.. note::

    Channel layers are an optional part of Channels, and can be disabled if you
    want (by setting the ``CHANNEL_LAYERS`` setting to an empty value).

(insert cross-process example here)

You can also send messages to a dedicated process that's listening on its own,
fixed channel name::

    # In a consumer
    self.channel_layer.send(
        "myproject.thumbnail_notifications",
        {
            "type": "thumbnail.generate",
            "id": 90902949,
        },
    )

You can read more about channel layers in :doc:`/topics/channel_layers`.


Django Integration
------------------

Channels ships with easy drop-in support for common Django features, like
sessions and authentication. You can combine authentication with your
WebSocket views by just adding the right middleware around them::

    application = ProtocolTypeRouter({
        "websocket": AuthMiddlewareStack(
            URLRouter([
                url("^front(end)/$", consumers.AsyncChatConsumer),
            ])
        ),
    })

For more, see :doc:`/topics/sessions` and :doc:`/topics/authentication`.
