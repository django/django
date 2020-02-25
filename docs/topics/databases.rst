Database Access
===============

The Django ORM is a synchronous piece of code, and so if you want to access
it from asynchronous code you need to do special handling to make sure its
connections are closed properly.

If you're using ``SyncConsumer``, or anything based on it - like
``JsonWebsocketConsumer`` - you don't need to do anything special, as all your
code is already run in a synchronous mode and Channels will do the cleanup
for you as part of the ``SyncConsumer`` code.

If you are writing asynchronous code, however, you will need to call
database methods in a safe, synchronous context, using ``database_sync_to_async``.


Database Connections
--------------------

Channels can potentially open a lot more database connections than you may be used to if you are using threaded consumers (synchronous ones) - it can open up to one connection per thread.

By default, the number of threads is set to "the number of CPUs * 5", so you may see up to this number of threads. If you want to change it, set the ``ASGI_THREADS`` environment variable to the maximum number you wish to allow.

To avoid having too many threads idling in connections, you can instead rewrite your code to use async consumers and only dip into threads when you need to use Django's ORM (using ``database_sync_to_async``).


database_sync_to_async
----------------------

``channels.db.database_sync_to_async`` is a version of ``asgiref.sync.sync_to_async``
that also cleans up database connections on exit.

To use it, write your ORM queries in a separate function or method, and then
call it with ``database_sync_to_async`` like so:

.. code-block:: python

    from channels.db import database_sync_to_async

    async def connect(self):
        self.username = await database_sync_to_async(self.get_name)()

    def get_name(self):
        return User.objects.all()[0].name

You can also use it as a decorator:

.. code-block:: python

    from channels.db import database_sync_to_async

    async def connect(self):
        self.username = await self.get_name()

    @database_sync_to_async
    def get_name(self):
        return User.objects.all()[0].name
