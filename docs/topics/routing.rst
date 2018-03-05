Routing
=======

While consumers are valid :doc:`ASGI </asgi>` applications, you don't want
to just write one and have that be the only thing you can give to protocol
servers like Daphne. Channels provides routing classes that allow you to
combine and stack your consumers (and any other valid ASGI application) to
dispatch based on what the connection is.

.. important::

    Channels routers only work on the *scope* level, not on the level of
    individual *events*, which means you can only have one consumer for any
    given connection. Routing is to work out what single consumer to give a
    connection, not how to spread events from one connection across
    multiple consumers.

Routers are themselves valid ASGI applications, and it's possible to nest them.
We suggest that you have a ``ProtocolTypeRouter`` as the root application of
your project - the one that you pass to protocol servers - and nest other,
more protocol-specific routing underneath there.

Channels expects you to be able to define a single *root application*, and
provide the path to it as the ``ASGI_APPLICATION`` setting (think of this as
being analagous to the ``ROOT_URLCONF`` setting in Django). There's no fixed
rule as to where you need to put the routing and the root application,
but we recommend putting them in a project-level file called ``routing.py``,
next to ``urls.py``. You can read more about deploying Channels projects and
settings in :doc:`/deploying`.

Here's an example of what that ``routing.py`` might look like::

    from django.conf.urls import url

    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack

    from chat.consumers import AdminChatConsumer, PublicChatConsumer
    from aprs_news.consumers import APRSNewsConsumer

    application = ProtocolTypeRouter({

        # WebSocket chat handler
        "websocket": AuthMiddlewareStack(
            URLRouter([
                url("^chat/admin/$", AdminChatConsumer),
                url("^chat/$", PublicChatConsumer),
            ])
        ),

        # Using the third-party project frequensgi, which provides an APRS protocol
        "aprs": APRSNewsConsumer,

    })

It's possible to have routers from third-party apps, too, or write your own,
but we'll go over the built-in Channels ones here.


ProtocolTypeRouter
------------------

``channels.routing.ProtocolTypeRouter``

This should be the
top level of your ASGI application stack and the main entry in your routing file.

It lets you dispatch to one of a number of other ASGI applications based on the
``type`` value present in the ``scope``. Protocols will define a fixed type
value that their scope contains, so you can use this to distinguish between
incoming connection types.

It takes a single argument - a dictionary mapping type names to ASGI
applications that serve them::

    ProtocolTypeRouter({
        "http": some_app,
        "websocket": some_other_app,
    })

If a ``http`` argument is not provided, it will default to the Django view
system's ASGI interface, ``channels.http.AsgiHandler``, which means that for
most projects that aren't doing custom long-poll HTTP handling, you can simply
not specify a ``http`` option and leave it to work the "normal" Django way.

If you want to split HTTP handling between long-poll handlers and Django views,
use a URLRouter with ``channels.http.AsgiHandler`` specified as the last entry
with a match-everything pattern.


URLRouter
---------

``channels.routing.URLRouter``

Routes ``http`` or ``websocket`` type connections via their HTTP path. Takes
a single argument, a list of Django URL objects (either ``path()`` or ``url()``)::

    URLRouter([
        url("^longpoll/$", LongPollConsumer),
        url("^notifications/(?P<stream>\w+)/$", LongPollConsumer),
        url("", AsgiHandler),
    ])

Any captured groups will be provided in ``scope`` as the key ``url_route``, a
dict with an ``args`` key containing a list of positional regex groups and a
``kwargs`` key with a dict of the named regex groups.

For example, to pull out the named group ``stream`` in the example above, you
would do this::

    stream = self.scope["url_route"]["kwargs"]["stream"]


ChannelNameRouter
-----------------

``channels.routing.ChannelNameRouter``

Routes ``channel`` type scopes based on the value of the ``channel`` key in
their scope. Intended for use with the :doc:`/topics/worker`.

It takes a single argument - a dictionary mapping channel names to ASGI
applications that serve them::

    ChannelNameRouter({
        "thumbnails-generate": some_app,
        "thunbnails-delete": some_other_app,
    })
