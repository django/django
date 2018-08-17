Deploying
=========

Channels 2 (ASGI) applications deploy similarly to WSGI applications - you load
them into a server, like Daphne, and you can scale the number of server
processes up and down.

The one optional extra requirement for a Channels project is to provision a
:doc:`channel layer </topics/channel_layers>`. Both steps are covered below.


Configuring the ASGI application
--------------------------------

The one setting that Channels needs to run is ``ASGI_APPLICATION``, which tells
Channels what the *root application* of your project is. As discussed in
:doc:`/topics/routing`, this is almost certainly going to be your top-level
(Protocol Type) router.

It should be a dotted path to the instance of the router; this is generally
going to be in a file like ``myproject/routing.py``::

    ASGI_APPLICATION = "myproject.routing.application"


Setting up a channel backend
----------------------------

.. note::

    This step is optional. If you aren't using the channel layer, skip this
    section.

Typically a channel backend will connect to one or more central servers that
serve as the communication layer - for example, the Redis backend connects
to a Redis server. All this goes into the ``CHANNEL_LAYERS`` setting;
here's an example for a remote Redis server::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("redis-server-name", 6379)],
            },
        },
    }

To use the Redis backend you have to install it::

    pip install -U channels_redis


Run protocol servers
--------------------

In order to talk to the outside world, your Channels/ASGI application needs
to be loaded into a *protocol server*. These can be like WSGI servers and run
your application in a HTTP mode, but they can also bridge to any number of
other protocols (chat protocols, IoT protocols, even radio networks).

All these servers have their own configuration options, but they all have
one thing in common - they will want you to pass them an ASGI application
to run. Because Django needs to run setup for things like models when it loads
in, you can't just pass in the same variable as you configured in
``ASGI_APPLICATION`` above; you need a bit more code to get Django ready.

In your project directory, you'll already have a file called ``wsgi.py`` that
does this to present Django as a WSGI application. Make a new file alongside it
called ``asgi.py`` and put this in it::

    """
    ASGI entrypoint. Configures Django and then runs the application
    defined in the ASGI_APPLICATION setting.
    """

    import os
    import django
    from channels.routing import get_default_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
    django.setup()
    application = get_default_application()

If you have any customizations in your ``wsgi.py`` to do additional things
on application start, or different ways of loading settings, you can do those
in here as well.

Now you have this file, all you need to do is pass the ``application`` object
inside it to your protocol server as the application it should run::

    daphne -p 8001 myproject.asgi:application


HTTP and WebSocket
------------------

While ASGI is a general protocol and we can't cover all possible servers here,
it's very likely you will want to deploy a Channels project to work over HTTP
and potentially WebSocket, so we'll cover that in some more detail.

The Channels project maintains an official ASGI HTTP/WebSocket server,
`Daphne <https://github.com/django/daphne>`_, and it's this that we'll talk about
configuring. Other HTTP/WebSocket ASGI servers are possible and will work just
as well provided they follow the spec, but will have different configuration.

You can choose to either use Daphne for all requests - HTTP and WebSocket -
or if you are conservative about stability, keep running standard HTTP requests
through a WSGI server and use Daphne only for things WSGI cannot do, like
HTTP long-polling and WebSockets. If you do split, you'll need to put something
in front of Daphne and your WSGI server to work out what requests to send to
each (using HTTP path or domain) - that's not covered here, just know you can
do it.

If you use Daphne for all traffic, it auto-negotiates between HTTP and WebSocket,
so there's no need to have your WebSockets on a separate domain or path (and
they'll be able to share cookies with your normal view code, which isn't
possible if you separate by domain rather than path).

To run Daphne, it just needs to be supplied with an application, much like
a WSGI server would need to be. Make sure you have an ``asgi.py`` file as
outlined above.

Then, you can run Daphne and supply the channel layer as the argument::

    daphne myproject.asgi:application

You should run Daphne inside either a process supervisor (systemd, supervisord)
or a container orchestration system (kubernetes, nomad) to ensure that it
gets restarted if needed and to allow you to scale the number of processes.

If you want to bind multiple Daphne instances to the same port on a machine,
use a process supervisor that can listen on ports and pass the file descriptors
to launched processes, and then pass the file descriptor with ``--fd NUM``.

You can also specify the port and IP that Daphne binds to::

    daphne -b 0.0.0.0 -p 8001 myproject.asgi:application

You can see more about Daphne and its options
`on GitHub <https://github.com/django/daphne>`_.

Alternative Web Servers
-----------------------

There are also alternative ASGI servers that you can use for serving Channels.

To some degree ASGI web servers should be interchangable, they should all have
the same basic functionality in terms of serving HTTP and WebSocket requests.

Aspects where servers may differ are in their configuration and defaults,
performance characteristics, support for resource limiting, differing protocol
and socket support, and approaches to process management.

Uvicorn
-------

`Uvicorn <https://www.uvicorn.org/>` is an ASGI & WSGI server, with a fast
uvloop + httptools implementation.

It supports HTTP/1 and websockets.

Hypercorn
---------

`Hypercorn <https://pgjones.gitlab.io/hypercorn/index.html>` is an ASGI
server based on the sans-io hyper, h11, h2, and wsproto libraries.

It supports HTTP/1, HTTP/2, and websockets.
