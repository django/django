Deploying
=========

Deploying applications using Channels requires a few more steps than a normal
Django WSGI application, but it's not very many.

Firstly, remember that even if you have Channels installed, it's an entirely
optional part of Django. If you leave a project with the default settings
(no ``CHANNEL_BACKENDS``), it'll just run and work like a normal WSGI app.

When you want to enable channels in production, you need to do three things:

* Set up a channel backend
* Run worker servers
* Run interface servers


Setting up a channel backend
----------------------------

The first step is to set up a channel backend. If you followed the
:doc:`getting-started` guide, you will have ended up using the database
backend, which is great for getting started quickly in development but totally
unsuitable for production use; it will hammer your database with lots of
queries as it polls for new messages.

Instead, take a look at the list of :doc:`backends`, and choose one that
fits your requirements (additionally, you could use a third-party pluggable
backend or write your own - that page also explains the interface and rules
a backend has to follow).

Typically a channel backend will connect to one or more central servers that
serve as the communication layer - for example, the Redis backend connects
to a Redis server. All this goes into the ``CHANNEL_BACKENDS`` setting;
here's an example for a remote Redis server::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "asgi_redis.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("redis-server-name", 6379)],
            },
            "ROUTING": "my_project.routing.channel_routing",
        },
    }

To use the Redis backend you have to install it::

    pip install -U asgi_redis


Make sure the same settings file is used across all your workers, interfaces
and WSGI apps; without it, they won't be able to talk to each other and things
will just fail to work.


Run worker servers
------------------

Because the work of running consumers is decoupled from the work of talking
to HTTP, WebSocket and other client connections, you need to run a cluster
of "worker servers" to do all the processing.

Each server is single-threaded, so it's recommended you run around one per
core on each machine; it's safe to run as many concurrent workers on the same
machine as you like, as they don't open any ports (all they do is talk to
the channel backend).

To run a worker server, just run::

    python manage.py runworker

Make sure you run this inside an init system or a program like supervisord that
can take care of restarting the process when it exits; the worker server has
no retry-on-exit logic, though it will absorb tracebacks from inside consumers
and forward them to stderr.

Make sure you keep an eye on how busy your workers are; if they get overloaded,
requests will take longer and longer to return as the messages queue up
(until the expiry limit is reached, at which point HTTP connections will
start dropping).

In a more complex project, you won't want all your channels being served by the
same workers, especially if you have long-running tasks (if you serve them from
the same workers as HTTP requests, there's a chance long-running tasks could
block up all the workers and delay responding to HTTP requests).

To manage this, it's possible to tell workers to either limit themselves to
just certain channel names or ignore specific channels using the
``--only-channels`` and ``--exclude-channels`` options. Here's an example
of configuring a worker to only serve HTTP and WebSocket requests::

    python manage.py runworker --only-channels=http.* --only-channels=websocket.*

Or telling a worker to ignore all messages on the "thumbnail" channel::

    python manage.py runworker --exclude-channels=thumbnail


Run interface servers
---------------------

The final piece of the puzzle is the "interface servers", the processes that
do the work of taking incoming requests and loading them into the channels
system.

You can just keep running your Django code as a WSGI app if you like, behind
something like uwsgi or gunicorn; this won't let you support WebSockets, though.
Still, if you want to use a WSGI server and have it talk to a worker server
cluster on the backend, see :ref:`wsgi-to-asgi`.

If you want to support WebSockets, long-poll HTTP requests and other Channels
features, you'll need to run a native ASGI interface server, as the WSGI
specification has no support for running these kinds of requests concurrently.
Channels ships with an interface server that we recommend you use called
`Daphne <http://github.com/andrewgodwin/daphne/>`_; it supports WebSockets,
long-poll HTTP requests, HTTP/2 *(soon)* and performs quite well.
Of course, any ASGI-compliant server will work!

Notably, Daphne has a nice feature where it supports all of these protocols on
the same port and on all paths; it auto-negotiates between HTTP and WebSocket,
so there's no need to have your WebSockets on a separate port or path (and
they'll be able to share cookies with your normal view code).

To run Daphne, it just needs to be supplied with a channel backend, in much
the same way a WSGI server needs to be given an application.
First, make sure your project has an ``asgi.py`` file that looks like this
(it should live next to ``wsgi.py``)::

    import os
    from channels.asgi import get_channel_layer

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_project.settings")

    channel_layer = get_channel_layer()

Then, you can run Daphne and supply the channel layer as the argument::

    daphne my_project.asgi:channel_layer

Like ``runworker``, you should place this inside an init system or something
like supervisord to ensure it is re-run if it exits unexpectedly.

If you only run Daphne and no workers, all of your page requests will seem to
hang forever; that's because Daphne doesn't have any worker servers to handle
the request and it's waiting for one to appear (while ``runserver`` also uses
Daphne, it launches a worker thread along with it in the same process). In this
scenario, it will eventually time out and give you a 503 error after 2 minutes;
you can configure how long it waits with the ``--http-timeout`` command line
argument.


Deploying new versions of code
------------------------------

One of the benefits of decoupling the client connection handling from work
processing is that it means you can run new code without dropping client
connections; this is especially useful for WebSockets.

Just restart your workers when you have new code (by default, if you send
them SIGTERM they'll cleanly exit and finish running any in-process
consumers), and any queued messages or new connections will go to the new
workers. As long as the new code is session-compatible, you can even do staged
rollouts to make sure workers on new code aren't experiencing high error rates.

There's no need to restart the WSGI or WebSocket interface servers unless
you've upgraded your version of Channels or changed any settings;
none of your code is used by them, and all middleware and code that can
customize requests is run on the consumers.

You can even use different Python versions for the interface servers and the
workers; the ASGI protocol that channel layers communicate over
is designed to be very portable and network-transparent.


.. _wsgi-to-asgi:

Running ASGI under WSGI
-----------------------

ASGI is a relatively new specification, and so it's backwards compatible with
WSGI servers with an adapter layer. You won't get WebSocket support this way -
WSGI doesn't support WebSockets - but you can run a separate ASGI server to
handle WebSockets if you want.

The ``asgiref`` package contains the adapter; all you need to do is put this
in your Django project's ``wsgi.py`` to declare a new WSGI application object
that backs onto ASGI underneath::

    import os
    from asgiref.wsgi import WsgiToAsgiAdapter
    from channels.asgi import get_channel_layer

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_test.settings")
    channel_layer = get_channel_layer()
    application = WsgiToAsgiAdapter(channel_layer)
