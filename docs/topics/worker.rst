Worker and Background Tasks
===========================

While :doc:`channel layers </topics/channel_layers>` are primarily designed for
communicating between different instances of ASGI applications, they can also
be used to offload work to a set of worker servers listening on fixed channel
names, as a simple, very-low-latency task queue.

.. note::

    The worker/background tasks system in Channels is simple and very fast,
    and achieves this by not having some features you may find useful, such as
    retries or return values.

    We recommend you use it for work that does not need guarantees around
    being complete (at-most-once delivery), and for work that needs more
    guarantees, look into a separate dedicated task queue like Celery.

Setting up background tasks works in two parts - sending the events, and then
setting up the consumers to receive and process the events.


Sending
-------

To send an event, just send it to a fixed channel name. For example, let's say
we want a background process that pre-caches thumbnails:

.. code-block:: python

    # Inside a consumer
    self.channel_layer.send(
        "thumbnails-generate",
        {
            "type": "generate",
            "id": 123456789,
        },
    )

Note that the event you send **must** have a ``type`` key, even if only one
type of message is being sent over the channel, as it will turn into an event
a consumer has to handle.

Also remember that if you are sending the event from a synchronous environment,
you have to use the ``asgiref.sync.async_to_sync`` wrapper as specified in
:doc:`channel layers </topics/channel_layers>`.

Receiving and Consumers
-----------------------

Channels will present incoming worker tasks to you as events inside a scope
with a ``type`` of ``channel``, and a ``channel`` key matching the channel
name. We recommend you use ProtocolTypeRouter and ChannelNameRouter (see
:doc:`/topics/routing` for more) to arrange your consumers:

.. code-block:: python

    application = ProtocolTypeRouter({
        ...
        "channel": ChannelNameRouter({
            "thumbnails-generate": consumers.GenerateConsumer,
            "thumbnails-delete": consumers.DeleteConsumer,
        }),
    })

You'll be specifying the ``type`` values of the individual events yourself
when you send them, so decide what your names are going to be and write
consumers to match. For example, here's a basic consumer that expects to
receive an event with ``type`` ``test.print``, and a ``text`` value containing
the text to print:

.. code-block:: python

    class PrintConsumer(SyncConsumer):
        def test_print(self, message):
            print("Test: " + message["text"])

Once you've hooked up the consumers, all you need to do is run a process that
will handle them. In lieu of a protocol server - as there are no connections
involved here - Channels instead provides you this with the ``runworker``
command:

.. code-block:: text

    python manage.py runworker thumbnails-generate thumbnails-delete

Note that ``runworker`` will only listen to the channels you pass it on the
command line. If you do not include a channel, or forget to run the worker,
your events will not be received and acted upon.
