SecurityMiddleware
==================

The ``djangosecure.middleware.SecurityMiddleware`` performs six different
tasks for you. Each one can be independently enabled or disabled with a
setting.

.. contents:: :local:


.. _x-frame-options:

X-Frame-Options: DENY
---------------------

.. note::

   Django 1.4+ provides `its own middleware and setting`_ to set the
   ``X-Frame-Options`` header; you can use either this or Django's, there's no
   value in using both.

`Clickjacking`_ attacks use layered frames to mislead users into clicking on a
different link from the one they think they are clicking on. Fortunately, newer
browsers support an ``X-Frame-Options`` header that allows you to limit or
prevent the display of your pages within a frame. Valid options are "DENY" or
"SAMEORIGIN" - the former prevents all framing of your site, and the latter
allows only sites within the same domain to frame.

Unless you have a need for frames, your best bet is to set "X-Frame-Options:
DENY" -- and this is what ``SecurityMiddleware`` will do for all responses, if
the :ref:`SECURE_FRAME_DENY` setting is ``True``.

If you have a few pages that should be frame-able, you can set the
"X-Frame-Options" header on the response to "SAMEORIGIN" in the view;
``SecurityMiddleware`` will not override an already-present "X-Frame-Options"
header. If you don't want the "X-Frame-Options" header on this view's response
at all, decorate the view with the ``frame_deny_exempt`` decorator::

    from djangosecure.decorators import frame_deny_exempt
    
    @frame_deny_exempt
    def my_view(request):
        # ...

.. _Clickjacking: http://www.sectheory.com/clickjacking.htm
.. _its own middleware and setting: https://docs.djangoproject.com/en/stable/ref/clickjacking/


.. _http-strict-transport-security:

HTTP Strict Transport Security
------------------------------

For sites that should only be accessed over HTTPS, you can instruct newer
browsers to refuse to connect to your domain name via an insecure connection
(for a given period of time) by setting the `"Strict-Transport-Security"
header`_. This reduces your exposure to some SSL-stripping man-in-the-middle
(MITM) attacks.

``SecurityMiddleware`` will set this header for you on all HTTPS responses if
you set the :ref:`SECURE_HSTS_SECONDS` setting to a nonzero integer value.

Additionally, if you set the :ref:`SECURE_HSTS_INCLUDE_SUBDOMAINS` setting to
``True``, ``SecurityMiddleware`` will add the ``includeSubDomains`` tag to the
``Strict-Transport-Security`` header. This is recommended, otherwise your site
may still be vulnerable via an insecure connection to a subdomain.

.. warning::
    The HSTS policy applies to your entire domain, not just the URL of the
    response that you set the header on. Therefore, you should only use it if
    your entire domain is served via HTTPS only.

.. warning::
    Browsers properly respecting the HSTS header will refuse to allow users to
    bypass warnings and connect to a site with an expired, self-signed, or
    otherwise invalid SSL certificate. If you use HSTS, make sure your
    certificates are in good shape and stay that way!

.. note::
    If you are deployed behind a load-balancer or reverse-proxy server, and the
    Strict-Transport-Security header is not being added to your responses, it
    may be because Django doesn't realize when it's on a secure connection; you
    may need to set the :ref:`SECURE_PROXY_SSL_HEADER` setting.

.. _"Strict-Transport-Security" header: http://en.wikipedia.org/wiki/Strict_Transport_Security


.. _x-content-type-options:

X-Content-Type-Options: nosniff
-------------------------------

Some browsers will try to guess the content types of the assets that they
fetch, overriding the ``Content-Type`` header. While this can help display
sites with improperly configured servers, it can also pose a security
risk.

If your site serves user-uploaded files, a malicious user could upload a
specially-crafted file that would be interpreted as HTML or Javascript by
the browser when you expected it to be something harmless.

To learn more about this header and how the browser treats it, you can
read about it on the `IE Security Blog`_.

To prevent the browser from guessing the content type, and force it to
always use the type provided in the ``Content-Type`` header, you can pass
the ``X-Content-Type-Options: nosniff`` header.  ``SecurityMiddleware`` will
do this for all responses if the :ref:`SECURE_CONTENT_TYPE_NOSNIFF` setting
is ``True``.

.. _IE Security Blog: http://blogs.msdn.com/b/ie/archive/2008/09/02/ie8-security-part-vi-beta-2-update.aspx


.. _x-xss-protection:

X-XSS-Protection: 1; mode=block
-------------------------------

Some browsers have to ability to block content that appears to be an `XSS
attack`_. They work by looking for Javascript content in the GET or POST
parameters of a page. If the Javascript is replayed in the server's
response the page is blocked from rendering and a error page is shown
instead.

The `X-XSS-Protection header`_ is used to control the operation of the
XSS filter.

To enable the XSS filter in the browser, and force it to always block
suspected XSS attacks, you can pass the ``X-XSS-Protection: 1; mode=block``
header. ``SecurityMiddleware`` will do this for all responses if the
:ref:`SECURE_BROWSER_XSS_FILTER` setting is ``True``.

.. warning::
    The XSS filter does not prevent XSS attacks on your site, and you
    should ensure that you are taking all other possible mesaures to
    prevent XSS attacks. The most obvious of these is validating and
    sanitizing all input.

.. _XSS attack: http://en.wikipedia.org/wiki/Cross-site_scripting
.. _X-XSS-Protection header: http://blogs.msdn.com/b/ie/archive/2008/07/02/ie8-security-part-iv-the-xss-filter.aspx


.. _ssl-redirect:

SSL Redirect
------------

If your site offers both HTTP and HTTPS connections, most users will end up
with an unsecured connection by default. For best security, you should redirect
all HTTP connections to HTTPS.

If you set the :ref:`SECURE_SSL_REDIRECT` setting to True,
``SecurityMiddleware`` will permanently (HTTP 301) redirect all HTTP
connections to HTTPS.

.. note::

    For performance reasons, it's preferable to do these redirects outside of
    Django, in a front-end loadbalancer or reverse-proxy server such as
    `nginx`_. In some deployment situations this isn't an option -
    :ref:`SECURE_SSL_REDIRECT` is intended for those cases.

If the :ref:`SECURE_SSL_HOST` setting has a value, all redirects will be sent
to that host instead of the originally-requested host.

If there are a few pages on your site that should be available over HTTP, and
not redirected to HTTPS, you can list regular expressions to match those URLs
in the :ref:`SECURE_REDIRECT_EXEMPT` setting.

.. note::
    If you are deployed behind a load-balancer or reverse-proxy server, and
    Django can't seem to tell when a request actually is already secure, you
    may need to set the :ref:`SECURE_PROXY_SSL_HEADER` setting.

.. _nginx: http://nginx.org


.. _proxied-ssl:

Detecting proxied SSL
---------------------

.. note::

   `Django 1.4+ offers the same functionality`_ built-in.  The Django setting
   works identically to this version.

In some deployment scenarios, Django's ``request.is_secure()`` method returns
``False`` even on requests that are actually secure, because the HTTPS
connection is made to a front-end loadbalancer or reverse-proxy, and the
internal proxied connection that Django sees is not HTTPS. Usually in these
cases the proxy server provides an alternative header to indicate the secured
external connection.

If this is your situation, you can set the :ref:`SECURE_PROXY_SSL_HEADER`
setting to a tuple of ("header", "value"); if "header" is set to "value" in
``request.META``, django-secure will tell Django to consider it a secure
request (in other words, ``request.is_secure()`` will return ``True`` for this
request). The "header" should be specified in the format it would be found in
``request.META`` (e.g. "HTTP_X_FORWARDED_PROTOCOL", not
"X-Forwarded-Protocol"). For example::

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTOCOL", "https")

.. warning::

   If you set this to a header that your proxy allows through from the request
   unmodified (i.e. a header that can be spoofed), you are allowing an attacker
   to pretend that any request is secure, even if it is not. Make sure you only
   use a header that your proxy sets unconditionally, overriding any value from
   the request.

.. _Django 1.4+ offers the same functionality: https://docs.djangoproject.com/en/stable/ref/settings/#secure-proxy-ssl-header
