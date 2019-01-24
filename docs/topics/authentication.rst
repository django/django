Authentication
==============

Channels supports standard Django authentication out-of-the-box for HTTP and
WebSocket consumers, and you can write your own middleware or handling code
if you want to support a different authentication scheme (for example,
tokens in the URL).


Django authentication
---------------------

The ``AuthMiddleware`` in Channels supports standard Django authentication,
where the user details are stored in the session. It allows read-only access
to a user object in the ``scope``.

``AuthMiddleware`` requires ``SessionMiddleware`` to function, which itself
requires ``CookieMiddleware``. For convenience, these are also provided
as a combined callable called ``AuthMiddlewareStack`` that includes all three.

To use the middleware, wrap it around the appropriate level of consumer
in your ``routing.py``::

    from django.conf.urls import url

    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack

    from myapp import consumers

    application = ProtocolTypeRouter({

        "websocket": AuthMiddlewareStack(
            URLRouter([
                url(r"^front(end)/$", consumers.AsyncChatConsumer),
            ])
        ),

    })

While you can wrap the middleware around each consumer individually,
it's recommended you wrap it around a higher-level application component,
like in this case the ``URLRouter``.

Note that the ``AuthMiddleware`` will only work on protocols that provide
HTTP headers in their ``scope`` - by default, this is HTTP and WebSocket.

To access the user, just use ``self.scope["user"]`` in your consumer code::


    class ChatConsumer(WebsocketConsumer):

        def connect(self, event):
            self.user = self.scope["user"]


Custom Authentication
---------------------

If you have a custom authentication scheme, you can write a custom middleware
to parse the details and put a user object (or whatever other object you need)
into your scope.

Middleware is written as a callable that takes an ASGI application and wraps
it to return another ASGI application. Most authentication can just be done
on the scope, so all you need to do is override the initial constructor
that takes a scope, rather than the event-running coroutine.

Here's a simple example of a middleware that just takes a user ID out of the
query string and uses that::

    from django.db import close_old_connections

    class QueryAuthMiddleware:
        """
        Custom middleware (insecure) that takes user IDs from the query string.
        """

        def __init__(self, inner):
            # Store the ASGI application we were passed
            self.inner = inner

        def __call__(self, scope):

            # Close old database connections to prevent usage of timed out connections
            close_old_connections()

            # Look up user from query string (you should also do things like
            # check it's a valid user ID, or if scope["user"] is already populated)
            user = User.objects.get(id=int(scope["query_string"]))

            # Return the inner application directly and let it run everything else
            return self.inner(dict(scope, user=user))

.. warning::

    Right now you will need to call ``close_old_connections()`` before any
    database code you call inside a middleware's scope-setup method to ensure
    you don't leak idle database connections. We hope to call this automatically
    in future versions of Channels.

The same principles can be applied to authenticate over non-HTTP protocols;
for example, you might want to use someone's chat username from a chat protocol
to turn it into a user.


How to log a user in/out
------------------------

Channels provides direct login and logout functions (much like Django's
``contrib.auth`` package does) as ``channels.auth.login`` and
``channels.auth.logout``.

Within your consumer you can await ``login(scope, user, backend=None)``
to log a user in. This requires that your scope has a ``session`` object;
the best way to do this is to ensure your consumer is wrapped in a
``SessionMiddlewareStack`` or a ``AuthMiddlewareStack``.

You can logout a user with the ``logout(scope)`` async function.

If you are in a WebSocket consumer, or logging-in after the first response
has been sent in a http consumer, the session is populated
**but will not be saved automatically** - you must call
``scope["session"].save()`` after login in your consumer code::

    from channels.auth import login

    class ChatConsumer(AsyncWebsocketConsumer):

        ...

        async def receive(self, text_data):
            ...
            # login the user to this session.
            await login(self.scope, user)
            # save the session (if the session backend does not access the db you can use `sync_to_async`)
            await database_sync_to_async(self.scope["session"].save)()

When calling ``login(scope, user)``, ``logout(scope)`` or ``get_user(scope)``
from a synchronous function you will need to wrap them in ``async_to_sync``,
as we only provide async versions::

    from asgiref.sync import async_to_sync
    from channels.auth import login

    class SyncChatConsumer(WebsocketConsumer):

        ...

        def receive(self, text_data):
            ...
            async_to_sync(login)(self.scope, user)
            self.scope["session"].save()

.. note::

    If you are using a long running consumer, websocket or long-polling
    HTTP it is possible that the user will be logged out of their session
    elsewhere while your consumer is running. You can periodically use
    ``get_user(scope)`` to be sure that the user is still logged in.
