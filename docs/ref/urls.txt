======================================
``django.conf.urls`` utility functions
======================================

.. module:: django.conf.urls

patterns()
----------

.. function:: patterns(prefix, pattern_description, ...)

A function that takes a prefix, and an arbitrary number of URL patterns, and
returns a list of URL patterns in the format Django needs.

The first argument to ``patterns()`` is a string ``prefix``. See
:ref:`The view prefix <urlpatterns-view-prefix>`.

The remaining arguments should be tuples in this format::

    (regular expression, Python callback function [, optional_dictionary [, optional_name]])

The ``optional_dictionary`` and ``optional_name`` parameters are described in
:ref:`Passing extra options to view functions <views-extra-options>`.

.. note::
    Because ``patterns()`` is a function call, it accepts a maximum of 255
    arguments (URL patterns, in this case). This is a limit for all Python
    function calls. This is rarely a problem in practice, because you'll
    typically structure your URL patterns modularly by using ``include()``
    sections. However, on the off-chance you do hit the 255-argument limit,
    realize that ``patterns()`` returns a Python list, so you can split up the
    construction of the list.

    ::

        urlpatterns = patterns('',
            ...
            )
        urlpatterns += patterns('',
            ...
            )

    Python lists have unlimited size, so there's no limit to how many URL
    patterns you can construct. The only limit is that you can only create 254
    at a time (the 255th argument is the initial prefix argument).

static()
--------

.. function:: static.static(prefix, view='django.views.static.serve', **kwargs)

Helper function to return a URL pattern for serving files in debug mode::

    from django.conf import settings
    from django.conf.urls.static import static

    urlpatterns = patterns('',
        # ... the rest of your URLconf goes here ...
    ) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

url()
-----

.. function:: url(regex, view, kwargs=None, name=None, prefix='')

You can use the ``url()`` function, instead of a tuple, as an argument to
``patterns()``. This is convenient if you want to specify a name without the
optional extra arguments dictionary. For example::

    urlpatterns = patterns('',
        url(r'^index/$', index_view, name="main-view"),
        ...
    )

This function takes five arguments, most of which are optional::

    url(regex, view, kwargs=None, name=None, prefix='')

See :ref:`Naming URL patterns <naming-url-patterns>` for why the ``name``
parameter is useful.

The ``prefix`` parameter has the same meaning as the first argument to
``patterns()`` and is only relevant when you're passing a string as the
``view`` parameter.

include()
---------

.. function:: include(module[, namespace=None, app_name=None])
              include(pattern_list)
              include((pattern_list, app_namespace, instance_namespace))

    A function that takes a full Python import path to another URLconf module
    that should be "included" in this place. Optionally, the :term:`application
    namespace` and :term:`instance namespace` where the entries will be included
    into can also be specified.

    ``include()`` also accepts as an argument either an iterable that returns
    URL patterns or a 3-tuple containing such iterable plus the names of the
    application and instance namespaces.

    :arg module: URLconf module (or module name)
    :arg namespace: Instance namespace for the URL entries being included
    :type namespace: string
    :arg app_name: Application namespace for the URL entries being included
    :type app_name: string
    :arg pattern_list: Iterable of URL entries as returned by :func:`patterns`
    :arg app_namespace: Application namespace for the URL entries being included
    :type app_namespace: string
    :arg instance_namespace: Instance namespace for the URL entries being included
    :type instance_namespace: string

See :ref:`including-other-urlconfs` and :ref:`namespaces-and-include`.

handler400
----------

.. data:: handler400

.. versionadded:: 1.6

A callable, or a string representing the full Python import path to the view
that should be called if the HTTP client has sent a request that caused an error
condition and a response with a status code of 400.

By default, this is ``'django.views.defaults.permission_denied'``. That default
value should suffice.

See the documentation about :ref:`the 400 (bad request) view
<http_bad_request_view>` for more information.

handler403
----------

.. data:: handler403

A callable, or a string representing the full Python import path to the view
that should be called if the user doesn't have the permissions required to
access a resource.

By default, this is ``'django.views.defaults.permission_denied'``. That default
value should suffice.

See the documentation about :ref:`the 403 (HTTP Forbidden) view
<http_forbidden_view>` for more information.

handler404
----------

.. data:: handler404

A callable, or a string representing the full Python import path to the view
that should be called if none of the URL patterns match.

By default, this is ``'django.views.defaults.page_not_found'``. That default
value should suffice.

See the documentation about :ref:`the 404 (HTTP Not Found) view
<http_not_found_view>` for more information.

handler500
----------

.. data:: handler500

A callable, or a string representing the full Python import path to the view
that should be called in case of server errors. Server errors happen when you
have runtime errors in view code.

By default, this is ``'django.views.defaults.server_error'``. That default
value should suffice.

See the documentation about :ref:`the 500 (HTTP Internal Server Error) view
<http_internal_server_error_view>` for more information.
