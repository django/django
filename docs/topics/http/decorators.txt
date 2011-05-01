===============
View decorators
===============

.. module:: django.views.decorators.http

Django provides several decorators that can be applied to views to support
various HTTP features.

Allowed HTTP methods
====================

The decorators in :mod:`django.views.decorators.http` can be used to restrict
access to views based on the request method. These decorators will return
a :class:`django.http.HttpResponseNotAllowed` if the conditions are not met.

.. function:: require_http_methods(request_method_list)

    Decorator to require that a view only accept particular request
    methods. Usage::

        from django.views.decorators.http import require_http_methods

        @require_http_methods(["GET", "POST"])
        def my_view(request):
            # I can assume now that only GET or POST requests make it this far
            # ...
            pass

    Note that request methods should be in uppercase.

.. function:: require_GET()

    Decorator to require that a view only accept the GET method.

.. function:: require_POST()

    Decorator to require that a view only accept the POST method.

.. function:: require_safe()

    .. versionadded:: 1.4

    Decorator to require that a view only accept the GET and HEAD methods.
    These methods are commonly considered "safe" because they should not have
    the significance of taking an action other than retrieving the requested
    resource.

    .. note::
        Django will automatically strip the content of responses to HEAD
        requests while leaving the headers unchanged, so you may handle HEAD
        requests exactly like GET requests in your views. Since some software,
        such as link checkers, rely on HEAD requests, you might prefer
        using ``require_safe`` instead of ``require_GET``.

Conditional view processing
===========================

The following decorators in :mod:`django.views.decorators.http` can be used to
control caching behavior on particular views.

.. function:: condition(etag_func=None, last_modified_func=None)

.. function:: etag(etag_func)

.. function:: last_modified(last_modified_func)

    These decorators can be used to generate ``ETag`` and ``Last-Modified``
    headers; see
    :doc:`conditional view processing </topics/conditional-view-processing>`.

.. module:: django.views.decorators.gzip

GZip compression
================

The decorators in :mod:`django.views.decorators.gzip` control content
compression on a per-view basis.

.. function:: gzip_page()

    This decorator compresses content if the browser allows gzip compression.
    It sets the ``Vary`` header accordingly, so that caches will base their
    storage on the ``Accept-Encoding`` header.

.. module:: django.views.decorators.vary

Vary headers
============

The decorators in :mod:`django.views.decorators.vary` can be used to control
caching based on specific request headers.

.. function:: vary_on_cookie(func)

.. function:: vary_on_headers(*headers)

    The ``Vary`` header defines which request headers a cache mechanism should take
    into account when building its cache key.

    See :ref:`using vary headers <using-vary-headers>`.
