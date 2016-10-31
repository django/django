Routing
=======

Routing in Channels is done using a system similar to that in core Django;
a list of possible routes is provided, and Channels goes through all routes
until a match is found, and then runs the resulting consumer.

The difference comes, however, in the fact that Channels has to route based
on more than just URL; channel name is the main thing routed on, and URL
path is one of many other optional things you can route on, depending on
the protocol (for example, imagine email consumers - they would route on
domain or recipient address instead).

The routing Channels takes is just a list of *routing objects* - the three
built in ones are ``route``, ``route_class`` and ``include``, but any object
that implements the routing interface will work:

* A method called ``match``, taking a single ``message`` as an argument and
  returning ``None`` for no match or a tuple of ``(consumer, kwargs)`` if matched.

* A method called ``channel_names``, which returns a set of channel names that
  will match, which is fed to the channel layer to listen on them.

The three default routing objects are:

* ``route``: Takes a channel name, a consumer function, and optional filter
  keyword arguments.

* ``route_class``: Takes a class-based consumer, and optional filter
  keyword arguments. Channel names are taken from the consumer's
  ``channel_names()`` method.

* ``include``: Takes either a list or string import path to a routing list,
  and optional filter keyword arguments.

.. _filters:

Filters
-------

Filtering is how you limit matches based on, for example, URLs; you use regular
expressions, like so::

    route("websocket.connect", consumers.ws_connect, path=r"^/chat/$")

.. note::
    Unlike Django's URL routing, which strips the first slash of a URL for
    neatness, Channels includes the first slash, as the routing system is
    generic and not designed just for URLs.

You can have multiple filters::

    route("email.receive", comment_response, to_address=r".*@example.com$", subject="^reply")

Multiple filters are always combined with logical AND; that is, you need to
match every filter to have the consumer called.

Filters can capture keyword arguments to be passed to your function or your class based consumer methods as a ``kwarg``::
    
    route("websocket.connect", connect_blog, path=r'^/liveblog/(?P<slug>[^/]+)/stream/$')

You can also specify filters on an ``include``::
    
    include("blog_includes", path=r'^/liveblog')

When you specify filters on ``include``, the matched portion of the attribute
is removed for matches inside the include; for example, this arrangement
matches URLs like ``/liveblog/stream/``, because the outside ``include``
strips off the ``/liveblog`` part it matches before passing it inside::

    inner_routes = [
        route("websocket.connect", connect_blog, path=r'^/stream/'),
    ]

    routing = [
        include(inner_routes, path=r'^/liveblog')
    ]

You can also include named capture groups in the filters on an include and
they'll be passed to the consumer just like those on ``route``; note, though,
that if the keyword argument names from the ``include`` and the ``route``
clash, the values from ``route`` will take precedence.
