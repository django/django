Backends
========

Multiple choices of backend are available, to fill different tradeoffs of
complexity, throughput and scalability. You can also write your own backend if
you wish; the API is very simple and documented below.

Redis
-----

The Redis backend is the recommended backend to run Channels with, as it
supports both high throughput on a single Redis server as well as the ability
to run against a set of Redis servers in a sharded mode.

To use the Redis backend you have to install the redis package::

    pip install -U redis

By default, it will attempt to connect to a Redis server on ``localhost:6379``,
but you can override this with the ``HOSTS`` setting::

    CHANNEL_BACKENDS = {
        "default": {
            "BACKEND": "channels.backends.redis_py.RedisChannelBackend",
            "HOSTS": [("redis-channel-1", 6379), ("redis-channel-2", 6379)],
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


In-memory
---------

The in-memory backend is the simplest, and not really a backend as such;
it exists purely to enable Django to run in a "normal" mode where no Channels
functionality is available, just normal HTTP request processing. You should
never need to set it explicitly.

This backend provides no network transparency or non-blocking guarantees.

Database
--------

=======
Writing Custom Backends
-----------------------

Backend Requirements
^^^^^^^^^^^^^^^^^^^^

While the channel backends are pluggable, there's a minimum standard they
must meet in terms of the way they perform.

In particular, a channel backend MUST:

* Provide a ``send()`` method which sends a message onto a named channel

* Provide a ``receive_many()`` method which returns an available message on the
  provided channels, or returns no message either instantly or after a short
  delay (it must not block indefinitely)

* Provide a ``group_add()`` method which adds a channel to a named group
  for at least the provided expiry period.

* Provide a ``group_discard()`` method with removes a channel from a named
  group if it was added, and nothing otherwise.

* Provide a ``group_members()`` method which returns an iterable of all
  channels currently in the group.

* Preserve the ordering of messages inside a channel

* Never deliver a message more than once (design for at-most-once delivery)

* Never block on sending of a message (dropping the message/erroring is preferable to blocking)

* Be able to store messages of at least 5MB in size

* Allow for channel and group names of up to 200 printable ASCII characters

* Expire messages only after the expiry period provided is up (a backend may
  keep them longer if it wishes, but should expire them at some reasonable
  point to ensure users do not come to rely on permanent messages)

In addition, it SHOULD:

* Provide a ``receive_many_blocking()`` method which is like ``receive_many()``
  but blocks until a message is available.

* Provide a ``send_group()`` method which sends a message to every channel
  in a group.

* Make ``send_group()`` perform better than ``O(n)``, where ``n`` is the
  number of members in the group; preferably send the messages to all
  members in a single call to your backing datastore or protocol.

* Try and preserve a rough global ordering, so that one busy channel does not
  drown out an old message in another channel if a worker is listening on both.

