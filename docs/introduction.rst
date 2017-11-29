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

If you haven't get installed Channels, you may want to read :doc:`installation`
first to get it installed. This introduction isn't a direct tutorial, but
you should be able to use it to follow along and make changes to an existing
Django project if you like.


Turtles All The Way Down
------------------------

Channels operates on the principle of "turtles all the way down" - we have
a basic idea of what a channels "application" is, and even the simplest of
*consumers* (the equivalent of Django views) are an entirely valid *ASGI*
application you can run by themselves.

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
receivers, and have that code sit alongside your existing code.

Our belief is that you want the ability to use safe, synchronous techniques
like Django views for most code, but have the option to drop down to a more
direct, asynchronous interface for complex tasks.


What is a Consumer?
-------------------

A consumer is the basic unit of Channels code. We call it a *consumer* as it
*consumes events*, but you can think of it as its own tiny little application.
When a request or new socket comes in, Channels will follow its routing table -
we'll look at that in a bit - find the right consumer for that incoming
connection, and start up a copy of it.

This means that, unlike Django views, consumers are long-running. They can
also be short-running - after all, HTTP requests can also be served by consumers -
but they're built around the idea of living for a little while.

A basic consumer looks like this::

    class ChatConsumer(WebsocketConsumer):

        def connect(self, message):
            self.username = "Anonymous"
            self.accept()
            self.send(text="[Welcome %s!]" % self.username)

        def receive(self, text, bytes=None):
            if text.startswith("/name"):
                self.username = text[5:].strip()
                self.send(text="[set your username to %s]" % self.username)
            else:
                self.send(text=self.username + ": " + text)

        def disconnect(self, message):
            pass

Each different protocol has different kinds of events that happen, and
each type is represented by a different method. You write code that handles
each event, and Channels will take care of scheduling them and running them
all in parallel.

Underneath, Channels is running on a fully asynchronous event loop, and
if you write code like above, it will get called in a synchronous thread.
This means you can safely do blocking operations, like calling the Django ORM::

    class LogConsumer(WebsocketConsumer)L

        def connect(self, message):
            Log.objects.create(
                type="connected",
                client=self.scope["client"],
            )

However, if you want more control and you're willing to work only in
asynchronous functions, you can write fully asynchronous consumers::

    class PingConsumer(AsyncConsumer):

        async def websocket_receive(self, message):
            await self.send({
                "type": "websocket.send",
                "text": "pong",
            })


Multiple Protocols
------------------

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

The goal of Channels is to let you build out your Django projects to work
across any protocol or transport you might encounter in the modern web, while
letting you work with the familiar components and coding style you're used to.


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

Channel layers are an optional part of Channels, and can be disabled if you
want (by setting the ``CHANNEL_LAYERS`` setting to an empty value).
