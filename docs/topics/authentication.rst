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

    class QueryAuthMiddleware:
        """
        Custom middleware (insecure) that takes user IDs from the query string.
        """

        def __init__(self, inner):
            # Store the ASGI application we were passed
            self.inner = inner

        def __call__(self, scope):
            # Look up user from query string (you should also do things like
            # check it's a valid user ID, or if scope["user"] is already populated)
            user = User.objects.get(id=int(scope["query_string"]))
            # Return the inner application directly and let it run everything else
            return self.inner(dict(scope, user=user))

The same principles can be applied to authenticate over non-HTTP protocols;
for example, you might want to use someone's chat username from a chat protocol
to turn it into a user.
