In Short
========


What is Channels?
-----------------

Channels extends Django to add :ref:`a new layer <what-are-channels>`
that allows two important features:

* WebSocket handling, in a way very :ref:`similar to normal views <websocket-example>`
* Background tasks, running in the same servers as the rest of Django


How?
----

It separates Django into two process types:

* One that handles HTTP and WebSockets
* One that runs views, websocket handlers and background tasks (*consumers*)

They communicate via a protocol called :doc:`ASGI <asgi>`, which is similar
to WSGI but runs over a network and allows for more protocol types.

Channels does not introduce asyncio, gevent, or any other async code to
your Django code; all of your business logic runs synchronously in a worker
process or thread.


I have to change how I run Django?
----------------------------------

No, all the new stuff is entirely optional. If you want it, however, you'll
change from running Django under a WSGI server, to running:

* An ASGI server, probably `Daphne <http://github.com/andrewgodwin/daphne/>`_
* Django worker servers, using ``manage.py runworker``
* Something to route ASGI requests over, like Redis or a database.


What else does Channels give me?
--------------------------------

Other features include:

* Easy HTTP long-poll support for thousands of clients at once
* Full session and auth support for WebSockets
* Automatic user login for WebSockets based on site cookies
* Built-in primitives for mass triggering of events (chat, live blogs, etc.)
* Zero-downtime deployment with browsers paused while new workers spin up
* Optional low-level HTTP control on a per-URL basis
* Extendability to other protocols or event sources (e.g. WebRTC, raw UDP, SMS)


Does it scale?
--------------

Yes, you can run any number of *protocol servers* (ones that serve HTTP
and WebSockets) and *worker servers* (ones that run your Django code) to
fit your use case.

The ASGI spec allows a number of different *channel layers* to be plugged in
between these two components, with difference performance characteristics, and
it's designed to allow both easy sharding as well as the ability to run
separate clusters with their own protocol and worker servers.


Do I need to worry about making all my code async-friendly?
-----------------------------------------------------------

No, all your code runs synchronously without any sockets or event loops to
block. You can use async code within a Django view or channel consumer if you
like - for example, to fetch lots of URLs in parallel - but it doesn't
affect the overall deployed site.


What version of Django does it work with?
-----------------------------------------

You can install Channels as a library for Django 1.8 and 1.9, and it (should be)
part of Django 1.10. It has a few extra dependencies, but these will all
be installed if you use ``pip``.


What do I read next?
--------------------

Start off by reading about the :doc:`concepts underlying Channels <concepts>`,
and then move on to read our example-laden :doc:`Getting Started guide <getting-started>`.
