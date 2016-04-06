Channel Layer Types
===================

Multiple choices of backend are available, to fill different tradeoffs of
complexity, throughput and scalability. You can also write your own backend if
you wish; the spec they confirm to is called :doc:`ASGI <asgi>`. Any
ASGI-compliant channel layer can be used.

Redis
-----

The Redis layer is the recommended backend to run Channels with, as it
supports both high throughput on a single Redis server as well as the ability
to run against a set of Redis servers in a sharded mode.

To use the Redis layer, simply install it from PyPI (it lives in a separate
package, as we didn't want to force a dependency on the redis-py for the main
install):

    pip install -U asgi_redis

By default, it will attempt to connect to a Redis server on ``localhost:6379``,
but you can override this with the ``hosts`` key in its config::

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "asgi_redis.RedisChannelLayer",
            "ROUTING": "???",
            "CONFIG": {
                "hosts": [("redis-channel-1", 6379), ("redis-channel-2", 6379)],
            },
        },
    }

Sharding
~~~~~~~~

The sharding model is based on consistent hashing - in particular,
:ref:`response channels <channel-types>` are hashed and used to pick a single
Redis server that both the interface server and the worker will use.

For normal channels, since any worker can service any channel request, messages
are simply distributed randomly among all possible servers, and workers will
pick a single server to listen to. Note that if you run more Redis servers than
workers, it's very likely that some servers will not have workers listening to
them; we recommend you always have at least ten workers for each Redis server
to ensure good distribution. Workers will, however, change server periodically
(every five seconds or so) so queued messages should eventually get a response.

Note that if you change the set of sharding servers you will need to restart
all interface servers and workers with the new set before anything works,
and any in-flight messages will be lost (even with persistence, some will);
the consistent hashing model relies on all running clients having the same
settings. Any misconfigured interface server or worker will drop some or all
messages.


Database
--------

The database layer is intended as a short-term solution for people who can't
use a more production-ready layer (for example, Redis), but still want something
that will work cross-process. It has poor performance, and is only
recommended for development or extremely small deployments.

This layer is included with Channels; just set your ``BACKEND`` to
``channels.database_layer.DatabaseChannelLayer``, and it will use the
default Django database alias to store messages. You can change the alias
by setting ``CONFIG`` to ``{'alias': 'aliasname'}``.

.. warning::
    The database channel layer is NOT fast, and performs especially poorly at
    latency and throughput. We recommend its use only as a last resort, and only
    on a database with good transaction support (e.g. Postgres), or you may
    get errors with multiple message delivery.


In-memory
---------

The in-memory layer is only useful when running the protocol server and the
worker server in a single process; the most common case of this
is ``runserver``, where a server thread, this channel layer, and worker thread all
co-exist inside the same python process.

Its path is ``asgiref.inmemory.ChannelLayer``. If you try and use this channel
layer with ``runworker``, it will exit, as it does not support cross-process
communication.


Writing Custom Channel Layers
-----------------------------

The interface channel layers present to Django and other software that
communicates over them is codified in a specification called :doc:`ASGI <asgi>`.

Any channel layer that conforms to the :doc:`ASGI spec <asgi>` can be used
by Django; just set ``BACKEND`` to the class to instantiate and ``CONFIG`` to
a dict of keyword arguments to initialize the class with.
