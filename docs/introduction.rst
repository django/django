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
