Security
========

This covers basic security for protocols you're serving via Channels and
helpers that we provide.


WebSockets
----------

WebSockets start out life as a HTTP request, including all the cookies
and headers, and so you can use the standard :doc:`/topics/authentication`
code in order to grab current sessions and check user IDs.

There is also a risk of cross-site request forgery (CSRF) with WebSockets though,
as they can be initiated from any site on the internet to your domain, and will
still have the user's cookies and session from your site. If you serve private
data down the socket, you should restrict the sites which are allowed to open
sockets to you.

This is done via the ``channels.security.websocket`` package, and the two
ASGI middlewares it contains, ``OriginValidator`` and
``AllowedHostsOriginValidator``.

``OriginValidator`` lets you restrict the valid options for the ``Origin``
header that is sent with every WebSocket to say where it comes from. Just wrap
it around your WebSocket application code like this, and pass it a list of
valid domains as the second argument. You can pass only a single domain (for example,
``.allowed-domain.com``) or a full origin, in the format ``scheme://domain[:port]``
(for example, ``http://allowed-domain.com:80``). Port is optional, but recommended:

.. code-block:: python

    from channels.security.websocket import OriginValidator

    application = ProtocolTypeRouter({

        "websocket": OriginValidator(
            AuthMiddlewareStack(
                URLRouter([
                    ...
                ])
            ),
            [".goodsite.com", "http://.goodsite.com:80", "http://other.site.com"],
        ),
    })

Note: If you want to resolve any domain, then use the origin ``*``.


Often, the set of domains you want to restrict to is the same as the Django
``ALLOWED_HOSTS`` setting, which performs a similar security check for the
``Host`` header, and so ``AllowedHostsOriginValidator`` lets you use this
setting without having to re-declare the list:

.. code-block:: python

    from channels.security.websocket import AllowedHostsOriginValidator

    application = ProtocolTypeRouter({

        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter([
                    ...
                ])
            ),
        ),
    })

``AllowedHostsOriginValidator`` will also automatically allow local connections
through if the site is in ``DEBUG`` mode, much like Django's host validation.
