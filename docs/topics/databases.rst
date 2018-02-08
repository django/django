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


database_sync_to_async
----------------------

``channels.db.database_sync_to_async`` is a version of ``asgiref.sync.sync_to_async``
that also cleans up database connections on exit.

To use it, write your ORM queries in a separate function or method, and then
call it with ``database_sync_to_async`` like so::

    from channels.db import database_sync_to_async

    async def connect(self):
        self.username = database_sync_to_async(self.get_name)()

    def get_name(self):
        return User.objects.all()[0].name

You can also use it as a decorator::

    from channels.db import database_sync_to_async

    async def connect(self):
        self.username = self.get_name()

    @database_sync_to_async
    def get_name(self):
        return User.objects.all()[0].name
