=================
The redirects app
=================

.. module:: django.contrib.redirects
   :synopsis: A framework for managing redirects.

Django comes with an optional redirects application. It lets you store simple
redirects in a database and handles the redirecting for you. It uses the HTTP
response status code ``301 Moved Permanently`` by default.

Installation
============

To install the redirects app, follow these steps:

1. Ensure that the ``django.contrib.sites`` framework
   :ref:`is installed <enabling-the-sites-framework>`.
2. Add ``'django.contrib.redirects'`` to your :setting:`INSTALLED_APPS` setting.
3. Add ``'django.contrib.redirects.middleware.RedirectFallbackMiddleware'``
   to your :setting:`MIDDLEWARE` setting.
4. Run the command :djadmin:`manage.py migrate <migrate>`.

How it works
============

``manage.py migrate`` creates a ``django_redirect`` table in your database. This
is a simple lookup table with ``site_id``, ``old_path`` and ``new_path`` fields.

The :class:`~django.contrib.redirects.middleware.RedirectFallbackMiddleware`
does all of the work. Each time any Django application raises a 404
error, this middleware checks the redirects database for the requested
URL as a last resort. Specifically, it checks for a redirect with the
given ``old_path`` with a site ID that corresponds to the
:setting:`SITE_ID` setting.

* If it finds a match, and ``new_path`` is not empty, it redirects to
  ``new_path`` using a 301 ("Moved Permanently") redirect. You can subclass
  :class:`~django.contrib.redirects.middleware.RedirectFallbackMiddleware`
  and set
  :attr:`~django.contrib.redirects.middleware.RedirectFallbackMiddleware.response_redirect_class`
  to :class:`django.http.HttpResponseRedirect` to use a
  ``302 Moved Temporarily`` redirect instead.
* If it finds a match, and ``new_path`` is empty, it sends a 410 ("Gone")
  HTTP header and empty (content-less) response.
* If it doesn't find a match, the request continues to be processed as
  usual.

The middleware only gets activated for 404s -- not for 500s or responses of any
other status code.

Note that the order of :setting:`MIDDLEWARE` matters. Generally, you can put
:class:`~django.contrib.redirects.middleware.RedirectFallbackMiddleware` at the
end of the list, because it's a last resort.

For more on middleware, read the :doc:`middleware docs
</topics/http/middleware>`.

How to add, change and delete redirects
=======================================

Via the admin interface
-----------------------

If you've activated the automatic Django admin interface, you should see a
"Redirects" section on the admin index page. Edit redirects as you edit any
other object in the system.

Via the Python API
------------------

.. class:: models.Redirect

    Redirects are represented by a standard :doc:`Django model </topics/db/models>`,
    which lives in `django/contrib/redirects/models.py`_. You can access redirect
    objects via the :doc:`Django database API </topics/db/queries>`.

.. _django/contrib/redirects/models.py: https://github.com/django/django/blob/master/django/contrib/redirects/models.py

Middleware
==========

.. class:: middleware.RedirectFallbackMiddleware

    You can change the :class:`~django.http.HttpResponse` classes used
    by the middleware by creating a subclass of
    :class:`~django.contrib.redirects.middleware.RedirectFallbackMiddleware`
    and overriding ``response_gone_class`` and/or ``response_redirect_class``.

    .. attribute:: response_gone_class

        The :class:`~django.http.HttpResponse` class used when a
        :class:`~django.contrib.redirects.models.Redirect` is not found for the
        requested path or has a blank ``new_path`` value.

        Defaults to :class:`~django.http.HttpResponseGone`.

    .. attribute:: response_redirect_class

        The :class:`~django.http.HttpResponse` class that handles the redirect.

        Defaults to :class:`~django.http.HttpResponsePermanentRedirect`.
