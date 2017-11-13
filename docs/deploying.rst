Deploying
=========

Channels 2 (ASGI) applications deploy similarly to WSGI applications - you load
them into a server, like Daphne, and you can scale the number of server
processes up and down.

The one extra requirement for a Channels project is to provision a *channel layer* -
a means for the different processes to talk to each other when they need to, for
example, broadcast events to each other. Both steps are covered below.


Setting up a channel backend
----------------------------

The first step is to set up a channel backend.

Typically a channel backend will connect to one or more central servers that
serve as the communication layer - for example, the Redis backend connects
to a Redis server. All this goes into the ``CHANNEL_LAYERS`` setting;
here's an example for a remote Redis server::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "asgi_redis.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("redis-server-name", 6379)],
            },
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
            "CONFIG": {
                "prefix": "mysite",
            },
        },
    }


Run servers
-----------

The Channels project maintains an official ASGI server, *Daphne*, but the
ASGI specification is documented to allow options between a number of servers
(or to let you choose frameworks other than Channels).

If you want to support WebSockets, long-poll HTTP requests and other Channels
features, you'll need to run a native ASGI interface server, as the WSGI
specification has no support for running these kinds of requests concurrently.

You can just keep running your "normal" Django code as a WSGI app if you like, behind
something like uwsgi or gunicorn; this won't let you support WebSockets, long-polling, or background async tasks though,
so you'll need to run a separate interface server to terminate those connections
and configure routing in front of your interface and WSGI servers to route
requests appropriately.

If you use Daphne for all traffic, it auto-negotiates between HTTP and WebSocket,
so there's no need to have your WebSockets on a separate domain or path (and
they'll be able to share cookies with your normal view code, which isn't
possible if you separate by domain rather than path).

To run Daphne, it just needs to be supplied with an application, much like
a WSGI server would need to be.

First, make sure your project has an ``asgi.py`` file that looks like this
(it should live next to ``wsgi.py`` - remember to change ``myproject`` below!)::

    import os
    import django
    from channels.routing import get_default_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
    django.setup()
    application = get_default_application()

Then, you can run Daphne and supply the channel layer as the argument::

    daphne my_project.asgi:application

You should place this inside either a process supervisor (systemd, supervisord)
or a container orchestration system (kubernetes, nomad) to ensure that it
gets restarted if needed and to allow you to scale the number of processes.

