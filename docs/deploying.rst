Deploying
=========

Deploying applications using channels requires a few more steps than a normal
Django WSGI application, but you have a couple of options as to how to deploy
it and how much of your traffic you wish to route through the channel layers.

Firstly, remember that it's an entirely optional part of Django.
If you leave a project with the default settings (no ``CHANNEL_LAYERS``),
it'll just run and work like a normal WSGI app.

When you want to enable channels in production, you need to do three things:

* Set up a channel backend
* Run worker servers
* Run interface servers

You can set things up in one of two ways; either route all traffic through
a :ref:`HTTP/WebSocket interface server <asgi-alone>`, removing the need
to run a WSGI server at all; or, just route WebSockets and long-poll
HTTP connections to the interface server, and :ref:`leave other pages served
by a standard WSGI server <wsgi-with-asgi>`.

Routing all traffic through the interface server lets you have WebSockets and
long-polling coexist in the same URL tree with no configuration; if you split
the traffic up, you'll need to configure a webserver or layer 7 loadbalancer
in front of the two servers to route requests to the correct place based on
path or domain. Both methods are covered below.


Setting up a channel backend
----------------------------

The first step is to set up a channel backend. If you followed the
:doc:`getting-started` guide, you will have ended up using the in-memory
backend, which is useful for ``runserver``, but as it only works inside the
same process, useless for actually running separate worker and interface
servers.

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

Some backends, though, don't require an extra server, like the IPC backend,
which works between processes on the same machine but not over the network
(it's available in the ``asgi_ipc`` package)::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "asgi_ipc.IPCChannelLayer",
            "ROUTING": "my_project.routing.channel_routing",
            "CONFIG": {
                "prefix": "mysite",
            },
        },
    }

Make sure the same settings file is used across all your workers and interface
servers; without it, they won't be able to talk to each other and things
will just fail to work.


Run worker servers
------------------

Because the work of running consumers is decoupled from the work of talking
to HTTP, WebSocket and other client connections, you need to run a cluster
of "worker servers" to do all the processing.

Each server is single-threaded, so it's recommended you run around one or two per
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
(until the expiry or capacity limit is reached, at which point HTTP connections will
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

If you want to support WebSockets, long-poll HTTP requests and other Channels
features, you'll need to run a native ASGI interface server, as the WSGI
specification has no support for running these kinds of requests concurrently.
We ship with an interface server that we recommend you use called
`Daphne <http://github.com/andrewgodwin/daphne/>`_; it supports WebSockets,
long-poll HTTP requests, HTTP/2 *(soon)* and performs quite well.

You can just keep running your Django code as a WSGI app if you like, behind
something like uwsgi or gunicorn; this won't let you support WebSockets, though,
so you'll need to run a separate interface server to terminate those connections
and configure routing in front of your interface and WSGI servers to route
requests appropriately.

If you use Daphne for all traffic, it auto-negotiates between HTTP and WebSocket,
so there's no need to have your WebSockets on a separate port or path (and
they'll be able to share cookies with your normal view code, which isn't
possible if you separate by domain rather than path).

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
Daphne, it launches worker threads along with it in the same process). In this
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
you've upgraded the interface server itself or changed the ``CHANNEL_LAYER``
setting; none of your code is used by them, and all middleware and code that can
customize requests is run on the consumers.

You can even use different Python versions for the interface servers and the
workers; the ASGI protocol that channel layers communicate over
is designed to be portable across all Python versions.


.. _asgi-alone:

Running just ASGI
-----------------

If you are just running Daphne to serve all traffic, then the configuration
above is enough where you can just expose it to the Internet and it'll serve
whatever kind of request comes in; for a small site, just the one Daphne
instance and four or five workers is likely enough.

However, larger sites will need to deploy things at a slightly larger scale,
and how you scale things up is different from WSGI; see :ref:`scaling-up`.


.. _wsgi-with-asgi:

Running ASGI alongside WSGI
---------------------------

ASGI and its canonical interface server Daphne are both relatively new,
and so you may not wish to run all your traffic through it yet (or you may
be using specialized features of your existing WSGI server).

If that's the case, that's fine; you can run Daphne and a WSGI server alongside
each other, and only have Daphne serve the requests you need it to (usually
WebSocket and long-poll HTTP requests, as these do not fit into the WSGI model).

To do this, just set up your Daphne to serve as we discussed above, and then
configure your load-balancer or front HTTP server process to dispatch requests
to the correct server - based on either path, domain, or if
you can, the Upgrade header.

Dispatching based on path or domain means you'll need to design your WebSocket
URLs carefully so you can always tell how to route them at the load-balancer
level; the ideal thing is to be able to look for the ``Upgrade: WebSocket``
header and distinguish connections by this, but not all software supports this
and it doesn't help route long-poll HTTP connections at all.

You could also invert this model, and have all connections go to Daphne by
default and selectively route some back to the WSGI server, if you have
particular URLs or domains you want to use that server on.


.. _scaling-up:

Scaling Up
----------

Scaling up a deployment containing channels (and thus running ASGI) is a little
different to scaling a WSGI deployment.

The fundamental difference is that the group mechanic requires all servers serving
the same site to be able to see each other; if you separate the site up and run
it in a few, large clusters, messages to groups will only deliver to WebSockets
connected to the same cluster. For some site designs this will be fine, and if
you think you can live with this and design around it (which means never
designing anything around global notifications or events), this may be a good
way to go.

For most projects, you'll need to run a single channel layer at scale in order
to achieve proper group delivery. Different backends will scale up differently,
but the Redis backend can use multiple Redis servers and spread the load
across them using sharding based on consistent hashing.

The key to a channel layer knowing how to scale a channel's delivery is if it
contains the ``!`` character or not, which signifies a single-reader channel.
Single-reader channels are only ever connected to by a single process, and so
in the Redis case are stored on a single, predictable shard. Other channels
are assumed to have many workers trying to read them, and so messages for
these can be evenly divided across all shards.

Django channels are still relatively new, and so it's likely that we don't yet
know the full story about how to scale things up; we run large load tests to
try and refine and improve large-project scaling, but it's no substitute for
actual traffic. If you're running channels at scale, you're encouraged to
send feedback to the Django team and work with us to hone the design and
performance of the channel layer backends, or you're free to make your own;
the ASGI specification is comprehensive and comes with a conformance test
suite, which should aid in any modification of existing backends or development
of new ones.
