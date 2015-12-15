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

    CHANNEL_BACKENDS = {
        "default": {
            "BACKEND": "channels.backends.redis_py.RedisChannelBackend",
            "HOSTS": [("redis-channel", 6379)],
        },
    }

To use the Redis backend you have to install the redis package::

    pip install -U redis


Make sure the same setting file is used across all your workers, interfaces
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

TODO: We should probably ship some kind of latency measuring tooling.


Run interface servers
---------------------

The final piece of the puzzle is the "interface servers", the processes that
do the work of taking incoming requests and loading them into the channels
system.

You can just keep running your Django code as a WSGI app if you like, behind
something like uwsgi or gunicorn, and just use the WSGI interface as the app
you load into the server - just set it to use
``channels.interfaces.wsgi:WSGIHandler``.

If you want to support WebSockets, however, you'll need to run another
interface server, as the WSGI protocol has no support for WebSockets.
Channels ships with an Autobahn-based WebSocket interface server
that should suit your needs; however, you could also use a third-party
interface server or write one yourself, as long as it follows the
:doc:`message-standards`.

Notably, it's possible to combine more than one protocol into the same
interface server, and the one Channels ships with does just this; it can
optionally serve HTTP requests as well as WebSockets, though by default
it will just serve WebSockets and assume you're routing requests to the right
kind of server using your load balancer or reverse proxy.

To run a normal WebSocket server, just run::

    python manage.py runwsserver

Like ``runworker``, you should place this inside an init system or something
like supervisord to ensure it is re-run if it exits unexpectedly.

If you want to enable serving of normal HTTP requests as well, just run::

    python manage.py runwsserver --accept-all

This interface server is built on in-process asynchronous solutions
(Twisted for Python 2, and asyncio for Python 3) and so should be able to
handle a lot of simultaneous connections. That said, you should still plan to
run a cluster of them and load-balance between them; the per-connection memory
overhead is moderately high.

Finally, note that it's entirely possible for interface servers to be written
in a language other than Python, though this would mean they could not take
advantage of the channel backend abstraction code and so they'd likely be
custom-written for a single channel backend.


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
customise requests is run on the consumers.
