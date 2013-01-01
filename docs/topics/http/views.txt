=============
Writing views
=============

A view function, or *view* for short, is simply a Python function that takes a
Web request and returns a Web response. This response can be the HTML contents
of a Web page, or a redirect, or a 404 error, or an XML document, or an image .
. . or anything, really. The view itself contains whatever arbitrary logic is
necessary to return that response. This code can live anywhere you want, as long
as it's on your Python path. There's no other requirement--no "magic," so to
speak. For the sake of putting the code *somewhere*, the convention is to
put views in a file called ``views.py``, placed in your project or
application directory.

A simple view
=============

Here's a view that returns the current date and time, as an HTML document:

.. code-block:: python

    from django.http import HttpResponse
    import datetime

    def current_datetime(request):
        now = datetime.datetime.now()
        html = "<html><body>It is now %s.</body></html>" % now
        return HttpResponse(html)

Let's step through this code one line at a time:

* First, we import the class :class:`~django.http.HttpResponse` from the
  :mod:`django.http` module, along with Python's ``datetime`` library.

* Next, we define a function called ``current_datetime``. This is the view
  function. Each view function takes an :class:`~django.http.HttpRequest`
  object as its first parameter, which is typically named ``request``.

  Note that the name of the view function doesn't matter; it doesn't have to
  be named in a certain way in order for Django to recognize it. We're
  calling it ``current_datetime`` here, because that name clearly indicates
  what it does.

* The view returns an :class:`~django.http.HttpResponse` object that
  contains the generated response. Each view function is responsible for
  returning an :class:`~django.http.HttpResponse` object. (There are
  exceptions, but we'll get to those later.)

.. admonition:: Django's Time Zone

    Django includes a :setting:`TIME_ZONE` setting that defaults to
    ``America/Chicago``. This probably isn't where you live, so you might want
    to change it in your settings file.

Mapping URLs to views
=====================

So, to recap, this view function returns an HTML page that includes the current
date and time. To display this view at a particular URL, you'll need to create a
*URLconf*; see :doc:`/topics/http/urls` for instructions.

Returning errors
================

Returning HTTP error codes in Django is easy. There are subclasses of
:class:`~django.http.HttpResponse` for a number of common HTTP status codes
other than 200 (which means *"OK"*). You can find the full list of available
subclasses in the :ref:`request/response <ref-httpresponse-subclasses>`
documentation.  Just return an instance of one of those subclasses instead of
a normal :class:`~django.http.HttpResponse` in order to signify an error. For
example::

    def my_view(request):
        # ...
        if foo:
            return HttpResponseNotFound('<h1>Page not found</h1>')
        else:
            return HttpResponse('<h1>Page was found</h1>')

There isn't a specialized subclass for every possible HTTP response code,
since many of them aren't going to be that common. However, as documented in
the :class:`~django.http.HttpResponse` documentation, you can also pass the
HTTP status code into the constructor for :class:`~django.http.HttpResponse`
to create a return class for any status code you like. For example::

    def my_view(request):
        # ...

        # Return a "created" (201) response code.
        return HttpResponse(status=201)

Because 404 errors are by far the most common HTTP error, there's an easier way
to handle those errors.

The Http404 exception
---------------------

.. class:: django.http.Http404()

When you return an error such as :class:`~django.http.HttpResponseNotFound`,
you're responsible for defining the HTML of the resulting error page::

    return HttpResponseNotFound('<h1>Page not found</h1>')

For convenience, and because it's a good idea to have a consistent 404 error page
across your site, Django provides an ``Http404`` exception. If you raise
``Http404`` at any point in a view function, Django will catch it and return the
standard error page for your application, along with an HTTP error code 404.

Example usage::

    from django.http import Http404

    def detail(request, poll_id):
        try:
            p = Poll.objects.get(pk=poll_id)
        except Poll.DoesNotExist:
            raise Http404
        return render_to_response('polls/detail.html', {'poll': p})

In order to use the ``Http404`` exception to its fullest, you should create a
template that is displayed when a 404 error is raised. This template should be
called ``404.html`` and located in the top level of your template tree.

.. _customizing-error-views:

Customizing error views
=======================

.. _http_not_found_view:

The 404 (page not found) view
-----------------------------

.. function:: django.views.defaults.page_not_found(request, template_name='404.html')

When you raise an ``Http404`` exception, Django loads a special view devoted
to handling 404 errors. By default, it's the view
``django.views.defaults.page_not_found``, which either produces a very simple
"Not Found" message or loads and renders the template ``404.html`` if you
created it in your root template directory.

The default 404 view will pass one variable to the template: ``request_path``,
which is the URL that resulted in the error.

The ``page_not_found`` view should suffice for 99% of Web applications, but if
you want to override it, you can specify ``handler404`` in your URLconf, like
so::

    handler404 = 'mysite.views.my_custom_404_view'

Behind the scenes, Django determines the 404 view by looking for
``handler404`` in your root URLconf, and falling back to
``django.views.defaults.page_not_found`` if you did not define one.

Three things to note about 404 views:

* The 404 view is also called if Django doesn't find a match after
  checking every regular expression in the URLconf.

* The 404 view is passed a :class:`~django.template.RequestContext` and
  will have access to variables supplied by your
  :setting:`TEMPLATE_CONTEXT_PROCESSORS` setting (e.g., ``MEDIA_URL``).

* If :setting:`DEBUG` is set to ``True`` (in your settings module), then
  your 404 view will never be used, and your URLconf will be displayed
  instead, with some debug information.

.. _http_internal_server_error_view:

The 500 (server error) view
----------------------------

Similarly, Django executes special-case behavior in the case of runtime errors
in view code. If a view results in an exception, Django will, by default, call
the view ``django.views.defaults.server_error``, which either produces a very
simple "Server Error" message or loads and renders the template ``500.html`` if
you created it in your root template directory.

The default 500 view passes no variables to the ``500.html`` template and is
rendered with an empty ``Context`` to lessen the chance of additional errors.

This ``server_error`` view should suffice for 99% of Web applications, but if
you want to override the view, you can specify ``handler500`` in your URLconf,
like so::

    handler500 = 'mysite.views.my_custom_error_view'

Behind the scenes, Django determines the 500 view by looking for
``handler500`` in your root URLconf, and falling back to
``django.views.defaults.server_error`` if you did not define one.

One thing to note about 500 views:

* If :setting:`DEBUG` is set to ``True`` (in your settings module), then
  your 500 view will never be used, and the traceback will be displayed
  instead, with some debug information.

.. _http_forbidden_view:

The 403 (HTTP Forbidden) view
-----------------------------

.. versionadded:: 1.4

In the same vein as the 404 and 500 views, Django has a view to handle 403
Forbidden errors. If a view results in a 403 exception then Django will, by
default, call the view ``django.views.defaults.permission_denied``.

This view loads and renders the template ``403.html`` in your root template
directory, or if this file does not exist, instead serves the text
"403 Forbidden", as per :rfc:`2616` (the HTTP 1.1 Specification).

``django.views.defaults.permission_denied`` is triggered by a
:exc:`~django.core.exceptions.PermissionDenied` exception. To deny access in a
view you can use code like this::

    from django.core.exceptions import PermissionDenied

    def edit(request, pk):
        if not request.user.is_staff:
            raise PermissionDenied
        # ...

It is possible to override ``django.views.defaults.permission_denied`` in the
same way you can for the 404 and 500 views by specifying a ``handler403`` in
your URLconf::

    handler403 = 'mysite.views.my_custom_permission_denied_view'
