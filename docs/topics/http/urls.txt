==============
URL dispatcher
==============

A clean, elegant URL scheme is an important detail in a high-quality Web
application. Django lets you design URLs however you want, with no framework
limitations.

There's no ``.php`` or ``.cgi`` required, and certainly none of that
``0,2097,1-1-1928,00`` nonsense.

See `Cool URIs don't change`_, by World Wide Web creator Tim Berners-Lee, for
excellent arguments on why URLs should be clean and usable.

.. _Cool URIs don't change: http://www.w3.org/Provider/Style/URI

Overview
========

To design URLs for an app, you create a Python module informally called a
**URLconf** (URL configuration). This module is pure Python code and is a
simple mapping between URL patterns (simple regular expressions) to Python
functions (your views).

This mapping can be as short or as long as needed. It can reference other
mappings. And, because it's pure Python code, it can be constructed
dynamically.

.. versionadded:: 1.4
    Django also provides a way to translate URLs according to the active
    language. See the :ref:`internationalization documentation
    <url-internationalization>` for more information.

.. _how-django-processes-a-request:

How Django processes a request
==============================

When a user requests a page from your Django-powered site, this is the
algorithm the system follows to determine which Python code to execute:

1. Django determines the root URLconf module to use. Ordinarily,
   this is the value of the :setting:`ROOT_URLCONF` setting, but if the incoming
   ``HttpRequest`` object has an attribute called ``urlconf`` (set by
   middleware :ref:`request processing <request-middleware>`), its value
   will be used in place of the :setting:`ROOT_URLCONF` setting.

2. Django loads that Python module and looks for the variable
   ``urlpatterns``. This should be a Python list, in the format returned by
   the function :func:`django.conf.urls.patterns`.

3. Django runs through each URL pattern, in order, and stops at the first
   one that matches the requested URL.

4. Once one of the regexes matches, Django imports and calls the given
   view, which is a simple Python function (or a :doc:`class based view
   </topics/class-based-views/index>`). The view gets passed an
   :class:`~django.http.HttpRequest` as its first argument and any values
   captured in the regex as remaining arguments.

5. If no regex matches, or if an exception is raised during any
   point in this process, Django invokes an appropriate
   error-handling view. See `Error handling`_ below.

Example
=======

Here's a sample URLconf::

    from django.conf.urls import patterns

    urlpatterns = patterns('',
        (r'^articles/2003/$', 'news.views.special_case_2003'),
        (r'^articles/(\d{4})/$', 'news.views.year_archive'),
        (r'^articles/(\d{4})/(\d{2})/$', 'news.views.month_archive'),
        (r'^articles/(\d{4})/(\d{2})/(\d+)/$', 'news.views.article_detail'),
    )

Notes:

* To capture a value from the URL, just put parenthesis around it.

* There's no need to add a leading slash, because every URL has that. For
  example, it's ``^articles``, not ``^/articles``.

* The ``'r'`` in front of each regular expression string is optional but
  recommended. It tells Python that a string is "raw" -- that nothing in
  the string should be escaped. See `Dive Into Python's explanation`_.

Example requests:

* A request to ``/articles/2005/03/`` would match the third entry in the
  list. Django would call the function
  ``news.views.month_archive(request, '2005', '03')``.

* ``/articles/2005/3/`` would not match any URL patterns, because the
  third entry in the list requires two digits for the month.

* ``/articles/2003/`` would match the first pattern in the list, not the
  second one, because the patterns are tested in order, and the first one
  is the first test to pass. Feel free to exploit the ordering to insert
  special cases like this.

* ``/articles/2003`` would not match any of these patterns, because each
  pattern requires that the URL end with a slash.

* ``/articles/2003/03/03/`` would match the final pattern. Django would call
  the function ``news.views.article_detail(request, '2003', '03', '03')``.

.. _Dive Into Python's explanation: http://diveintopython.net/regular_expressions/street_addresses.html#re.matching.2.3

Named groups
============

The above example used simple, *non-named* regular-expression groups (via
parenthesis) to capture bits of the URL and pass them as *positional* arguments
to a view. In more advanced usage, it's possible to use *named*
regular-expression groups to capture URL bits and pass them as *keyword*
arguments to a view.

In Python regular expressions, the syntax for named regular-expression groups
is ``(?P<name>pattern)``, where ``name`` is the name of the group and
``pattern`` is some pattern to match.

Here's the above example URLconf, rewritten to use named groups::

    urlpatterns = patterns('',
        (r'^articles/2003/$', 'news.views.special_case_2003'),
        (r'^articles/(?P<year>\d{4})/$', 'news.views.year_archive'),
        (r'^articles/(?P<year>\d{4})/(?P<month>\d{2})/$', 'news.views.month_archive'),
        (r'^articles/(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/$', 'news.views.article_detail'),
    )

This accomplishes exactly the same thing as the previous example, with one
subtle difference: The captured values are passed to view functions as keyword
arguments rather than positional arguments. For example:

* A request to ``/articles/2005/03/`` would call the function
  ``news.views.month_archive(request, year='2005', month='03')``, instead
  of ``news.views.month_archive(request, '2005', '03')``.

* A request to ``/articles/2003/03/03/`` would call the function
  ``news.views.article_detail(request, year='2003', month='03', day='03')``.

In practice, this means your URLconfs are slightly more explicit and less prone
to argument-order bugs -- and you can reorder the arguments in your views'
function definitions. Of course, these benefits come at the cost of brevity;
some developers find the named-group syntax ugly and too verbose.

The matching/grouping algorithm
-------------------------------

Here's the algorithm the URLconf parser follows, with respect to named groups
vs. non-named groups in a regular expression:

1. If there are any named arguments, it will use those, ignoring non-named
   arguments.

2. Otherwise, it will pass all non-named arguments as positional arguments.

In both cases, any extra keyword arguments that have been given as per `Passing
extra options to view functions`_ (below) will also be passed to the view.

What the URLconf searches against
=================================

The URLconf searches against the requested URL, as a normal Python string. This
does not include GET or POST parameters, or the domain name.

For example, in a request to ``http://www.example.com/myapp/``, the URLconf
will look for ``myapp/``.

In a request to ``http://www.example.com/myapp/?page=3``, the URLconf will look
for ``myapp/``.

The URLconf doesn't look at the request method. In other words, all request
methods -- ``POST``, ``GET``, ``HEAD``, etc. -- will be routed to the same
function for the same URL.

Notes on capturing text in URLs
===============================

Each captured argument is sent to the view as a plain Python string, regardless
of what sort of match the regular expression makes. For example, in this
URLconf line::

    (r'^articles/(?P<year>\d{4})/$', 'news.views.year_archive'),

...the ``year`` argument to ``news.views.year_archive()`` will be a string, not
an integer, even though the ``\d{4}`` will only match integer strings.

A convenient trick is to specify default parameters for your views' arguments.
Here's an example URLconf and view::

    # URLconf
    urlpatterns = patterns('',
        (r'^blog/$', 'blog.views.page'),
        (r'^blog/page(?P<num>\d+)/$', 'blog.views.page'),
    )

    # View (in blog/views.py)
    def page(request, num="1"):
        # Output the appropriate page of blog entries, according to num.

In the above example, both URL patterns point to the same view --
``blog.views.page`` -- but the first pattern doesn't capture anything from the
URL. If the first pattern matches, the ``page()`` function will use its
default argument for ``num``, ``"1"``. If the second pattern matches,
``page()`` will use whatever ``num`` value was captured by the regex.

Performance
===========

Each regular expression in a ``urlpatterns`` is compiled the first time it's
accessed. This makes the system blazingly fast.

Syntax of the urlpatterns variable
==================================

``urlpatterns`` should be a Python list, in the format returned by the function
:func:`django.conf.urls.patterns`. Always use ``patterns()`` to create
the ``urlpatterns`` variable.

Error handling
==============

When Django can't find a regex matching the requested URL, or when an
exception is raised, Django will invoke an error-handling view.

The views to use for these cases are specified by three variables. Their
default values should suffice for most projects, but further customization is
possible by assigning values to them.

See the documentation on :ref:`customizing error views
<customizing-error-views>` for the full details.

Such values can be set in your root URLconf. Setting these variables in any
other URLconf will have no effect.

Values must be callables, or strings representing the full Python import path
to the view that should be called to handle the error condition at hand.

The variables are:

* ``handler404`` -- See :data:`django.conf.urls.handler404`.
* ``handler500`` -- See :data:`django.conf.urls.handler500`.
* ``handler403`` -- See :data:`django.conf.urls.handler403`.

.. versionadded:: 1.4
    ``handler403`` is new in Django 1.4.

.. _urlpatterns-view-prefix:

The view prefix
===============

You can specify a common prefix in your ``patterns()`` call, to cut down on
code duplication.

Here's the example URLconf from the :doc:`Django overview </intro/overview>`::

    from django.conf.urls import patterns

    urlpatterns = patterns('',
        (r'^articles/(\d{4})/$', 'news.views.year_archive'),
        (r'^articles/(\d{4})/(\d{2})/$', 'news.views.month_archive'),
        (r'^articles/(\d{4})/(\d{2})/(\d+)/$', 'news.views.article_detail'),
    )

In this example, each view has a common prefix -- ``'news.views'``.
Instead of typing that out for each entry in ``urlpatterns``, you can use the
first argument to the ``patterns()`` function to specify a prefix to apply to
each view function.

With this in mind, the above example can be written more concisely as::

    from django.conf.urls import patterns

    urlpatterns = patterns('news.views',
        (r'^articles/(\d{4})/$', 'year_archive'),
        (r'^articles/(\d{4})/(\d{2})/$', 'month_archive'),
        (r'^articles/(\d{4})/(\d{2})/(\d+)/$', 'article_detail'),
    )

Note that you don't put a trailing dot (``"."``) in the prefix. Django puts
that in automatically.

Multiple view prefixes
----------------------

In practice, you'll probably end up mixing and matching views to the point
where the views in your ``urlpatterns`` won't have a common prefix. However,
you can still take advantage of the view prefix shortcut to remove duplication.
Just add multiple ``patterns()`` objects together, like this:

Old::

    from django.conf.urls import patterns

    urlpatterns = patterns('',
        (r'^$', 'myapp.views.app_index'),
        (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'myapp.views.month_display'),
        (r'^tag/(?P<tag>\w+)/$', 'weblog.views.tag'),
    )

New::

    from django.conf.urls import patterns

    urlpatterns = patterns('myapp.views',
        (r'^$', 'app_index'),
        (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$','month_display'),
    )

    urlpatterns += patterns('weblog.views',
        (r'^tag/(?P<tag>\w+)/$', 'tag'),
    )

.. _including-other-urlconfs:

Including other URLconfs
========================

At any point, your ``urlpatterns`` can "include" other URLconf modules. This
essentially "roots" a set of URLs below other ones.

For example, here's an excerpt of the URLconf for the `Django Web site`_
itself. It includes a number of other URLconfs::

    from django.conf.urls import patterns, include

    urlpatterns = patterns('',
        # ... snip ...
        (r'^comments/', include('django.contrib.comments.urls')),
        (r'^community/', include('django_website.aggregator.urls')),
        (r'^contact/', include('django_website.contact.urls')),
        (r'^r/', include('django.conf.urls.shortcut')),
        # ... snip ...
    )

Note that the regular expressions in this example don't have a ``$``
(end-of-string match character) but do include a trailing slash. Whenever
Django encounters ``include()`` (:func:`django.conf.urls.include()`), it chops
off whatever part of the URL matched up to that point and sends the remaining
string to the included URLconf for further processing.

Another possibility is to include additional URL patterns not by specifying the
URLconf Python module defining them as the ``include()`` argument but by using
directly the pattern list as returned by :func:`~django.conf.urls.patterns`
instead. For example, consider this URLconf::

    from django.conf.urls import patterns, url, include

    extra_patterns = patterns('',
        url(r'^reports/(?P<id>\d+)/$', 'credit.views.report'),
        url(r'^charge/$', 'credit.views.charge'),
    )

    urlpatterns = patterns('',
        url(r'^$', 'apps.main.views.homepage'),
        (r'^help/', include('apps.help.urls')),
        (r'^credit/', include(extra_patterns)),
    )

In this example, the ``/credit/reports/`` URL will be handled by the
``credit.views.report()`` Django view.

.. _`Django Web site`: https://www.djangoproject.com/

Captured parameters
-------------------

An included URLconf receives any captured parameters from parent URLconfs, so
the following example is valid::

    # In settings/urls/main.py
    urlpatterns = patterns('',
        (r'^(?P<username>\w+)/blog/', include('foo.urls.blog')),
    )

    # In foo/urls/blog.py
    urlpatterns = patterns('foo.views',
        (r'^$', 'blog.index'),
        (r'^archive/$', 'blog.archive'),
    )

In the above example, the captured ``"username"`` variable is passed to the
included URLconf, as expected.

.. _views-extra-options:

Passing extra options to view functions
=======================================

URLconfs have a hook that lets you pass extra arguments to your view functions,
as a Python dictionary.

Any URLconf tuple can have an optional third element, which should be a
dictionary of extra keyword arguments to pass to the view function.

For example::

    urlpatterns = patterns('blog.views',
        (r'^blog/(?P<year>\d{4})/$', 'year_archive', {'foo': 'bar'}),
    )

In this example, for a request to ``/blog/2005/``, Django will call
``blog.views.year_archive(year='2005', foo='bar')``.

This technique is used in the
:doc:`syndication framework </ref/contrib/syndication>` to pass metadata and
options to views.

.. admonition:: Dealing with conflicts

    It's possible to have a URL pattern which captures named keyword arguments,
    and also passes arguments with the same names in its dictionary of extra
    arguments. When this happens, the arguments in the dictionary will be used
    instead of the arguments captured in the URL.

Passing extra options to ``include()``
--------------------------------------

Similarly, you can pass extra options to :func:`~django.conf.urls.include`.
When you pass extra options to ``include()``, *each* line in the included
URLconf will be passed the extra options.

For example, these two URLconf sets are functionally identical:

Set one::

    # main.py
    urlpatterns = patterns('',
        (r'^blog/', include('inner'), {'blogid': 3}),
    )

    # inner.py
    urlpatterns = patterns('',
        (r'^archive/$', 'mysite.views.archive'),
        (r'^about/$', 'mysite.views.about'),
    )

Set two::

    # main.py
    urlpatterns = patterns('',
        (r'^blog/', include('inner')),
    )

    # inner.py
    urlpatterns = patterns('',
        (r'^archive/$', 'mysite.views.archive', {'blogid': 3}),
        (r'^about/$', 'mysite.views.about', {'blogid': 3}),
    )

Note that extra options will *always* be passed to *every* line in the included
URLconf, regardless of whether the line's view actually accepts those options
as valid. For this reason, this technique is only useful if you're certain that
every view in the included URLconf accepts the extra options you're passing.

Passing callable objects instead of strings
===========================================

Some developers find it more natural to pass the actual Python function object
rather than a string containing the path to its module. This alternative is
supported -- you can pass any callable object as the view.

For example, given this URLconf in "string" notation::

    urlpatterns = patterns('',
        (r'^archive/$', 'mysite.views.archive'),
        (r'^about/$', 'mysite.views.about'),
        (r'^contact/$', 'mysite.views.contact'),
    )

You can accomplish the same thing by passing objects rather than strings. Just
be sure to import the objects::

    from mysite.views import archive, about, contact

    urlpatterns = patterns('',
        (r'^archive/$', archive),
        (r'^about/$', about),
        (r'^contact/$', contact),
    )

The following example is functionally identical. It's just a bit more compact
because it imports the module that contains the views, rather than importing
each view individually::

    from mysite import views

    urlpatterns = patterns('',
        (r'^archive/$', views.archive),
        (r'^about/$', views.about),
        (r'^contact/$', views.contact),
    )

The style you use is up to you.

Note that if you use this technique -- passing objects rather than strings --
the view prefix (as explained in "The view prefix" above) will have no effect.

Note that :doc:`class based views</topics/class-based-views/index>` must be
imported::

    from mysite.views import ClassBasedView

    urlpatterns = patterns('',
        (r'^myview/$', ClassBasedView.as_view()),
    )

Reverse resolution of URLs
==========================

A common need when working on a Django project is the possibility to obtain URLs
in their final forms either for embedding in generated content (views and assets
URLs, URLs shown to the user, etc.) or for handling of the navigation flow on
the server side (redirections, etc.)

It is strongly desirable not having to hard-code these URLs (a laborious,
non-scalable and error-prone strategy) or having to devise ad-hoc mechanisms for
generating URLs that are parallel to the design described by the URLconf and as
such in danger of producing stale URLs at some point.

In other words, what's needed is a DRY mechanism. Among other advantages it
would allow evolution of the URL design without having to go all over the
project source code to search and replace outdated URLs.

The piece of information we have available as a starting point to get a URL is
an identification (e.g. the name) of the view in charge of handling it, other
pieces of information that necessarily must participate in the lookup of the
right URL are the types (positional, keyword) and values of the view arguments.

Django provides a solution such that the URL mapper is the only repository of
the URL design. You feed it with your URLconf and then it can be used in both
directions:

* Starting with a URL requested by the user/browser, it calls the right Django
  view providing any arguments it might need with their values as extracted from
  the URL.

* Starting with the identification of the corresponding Django view plus the
  values of arguments that would be passed to it, obtain the associated URL.

The first one is the usage we've been discussing in the previous sections. The
second one is what is known as *reverse resolution of URLs*, *reverse URL
matching*, *reverse URL lookup*, or simply *URL reversing*.

Django provides tools for performing URL reversing that match the different
layers where URLs are needed:

* In templates: Using the :ttag:`url` template tag.

* In Python code: Using the :func:`django.core.urlresolvers.reverse`
  function.

* In higher level code related to handling of URLs of Django model instances:
  The :meth:`~django.db.models.Model.get_absolute_url` method.

Examples
--------

Consider again this URLconf entry::

    from django.conf.urls import patterns, url

    urlpatterns = patterns('',
        #...
        url(r'^articles/(\d{4})/$', 'news.views.year_archive'),
        #...
    )

According to this design, the URL for the archive corresponding to year *nnnn*
is ``/articles/nnnn/``.

You can obtain these in template code by using:

.. code-block:: html+django

    <a href="{% url 'news.views.year_archive' 2012 %}">2012 Archive</a>
    {# Or with the year in a template context variable: #}
    <ul>
    {% for yearvar in year_list %}
    <li><a href="{% url 'news.views.year_archive' yearvar %}">{{ yearvar }} Archive</a></li>
    {% endfor %}
    </ul>

Or in Python code::

    from django.core.urlresolvers import reverse
    from django.http import HttpResponseRedirect

    def redirect_to_year(request):
        # ...
        year = 2006
        # ...
        return HttpResponseRedirect(reverse('news.views.year_archive', args=(year,)))

If, for some reason, it was decided that the URLs where content for yearly
article archives are published at should be changed then you would only need to
change the entry in the URLconf.

In some scenarios where views are of a generic nature, a many-to-one
relationship might exist between URLs and views. For these cases the view name
isn't a good enough identificator for it when it comes the time of reversing
URLs. Read the next section to know about the solution Django provides for this.

.. _naming-url-patterns:

Naming URL patterns
===================

It's fairly common to use the same view function in multiple URL patterns in
your URLconf. For example, these two URL patterns both point to the ``archive``
view::

    urlpatterns = patterns('',
        (r'^archive/(\d{4})/$', archive),
        (r'^archive-summary/(\d{4})/$', archive, {'summary': True}),
    )

This is completely valid, but it leads to problems when you try to do reverse
URL matching (through the :func:`~django.core.urlresolvers.reverse` function
or the :ttag:`url` template tag). Continuing this example, if you wanted to
retrieve the URL for the ``archive`` view, Django's reverse URL matcher would
get confused, because *two* URL patterns point at that view.

To solve this problem, Django supports **named URL patterns**. That is, you can
give a name to a URL pattern in order to distinguish it from other patterns
using the same view and parameters. Then, you can use this name in reverse URL
matching.

Here's the above example, rewritten to use named URL patterns::

    urlpatterns = patterns('',
        url(r'^archive/(\d{4})/$', archive, name="full-archive"),
        url(r'^archive-summary/(\d{4})/$', archive, {'summary': True}, "arch-summary"),
    )

With these names in place (``full-archive`` and ``arch-summary``), you can
target each pattern individually by using its name:

.. code-block:: html+django

    {% url 'arch-summary' 1945 %}
    {% url 'full-archive' 2007 %}

Even though both URL patterns refer to the ``archive`` view here, using the
``name`` parameter to ``url()`` allows you to tell them apart in templates.

The string used for the URL name can contain any characters you like. You are
not restricted to valid Python names.

.. note::

    When you name your URL patterns, make sure you use names that are unlikely
    to clash with any other application's choice of names. If you call your URL
    pattern ``comment``, and another application does the same thing, there's
    no guarantee which URL will be inserted into your template when you use
    this name.

    Putting a prefix on your URL names, perhaps derived from the application
    name, will decrease the chances of collision. We recommend something like
    ``myapp-comment`` instead of ``comment``.

.. _topics-http-defining-url-namespaces:

URL namespaces
==============

Introduction
------------

When you need to deploy multiple instances of a single application, it can be
helpful to be able to differentiate between instances. This is especially
important when using :ref:`named URL patterns <naming-url-patterns>`, since
multiple instances of a single application will share named URLs. Namespaces
provide a way to tell these named URLs apart.

A URL namespace comes in two parts, both of which are strings:

.. glossary::

  application namespace
    This describes the name of the application that is being deployed. Every
    instance of a single application will have the same application namespace.
    For example, Django's admin application has the somewhat predictable
    application namespace of ``'admin'``.

  instance namespace
    This identifies a specific instance of an application. Instance namespaces
    should be unique across your entire project. However, an instance namespace
    can be the same as the application namespace. This is used to specify a
    default instance of an application. For example, the default Django Admin
    instance has an instance namespace of ``'admin'``.

Namespaced URLs are specified using the ``':'`` operator. For example, the main
index page of the admin application is referenced using ``'admin:index'``. This
indicates a namespace of ``'admin'``, and a named URL of ``'index'``.

Namespaces can also be nested. The named URL ``'foo:bar:whiz'`` would look for
a pattern named ``'whiz'`` in the namespace ``'bar'`` that is itself defined
within the top-level namespace ``'foo'``.

.. _topics-http-reversing-url-namespaces:

Reversing namespaced URLs
-------------------------

When given a namespaced URL (e.g. ``'myapp:index'``) to resolve, Django splits
the fully qualified name into parts, and then tries the following lookup:

1. First, Django looks for a matching :term:`application namespace` (in this
   example, ``'myapp'``). This will yield a list of instances of that
   application.

2. If there is a *current* application defined, Django finds and returns
   the URL resolver for that instance. The *current* application can be
   specified as an attribute on the template context - applications that
   expect to have multiple deployments should set the ``current_app``
   attribute on any ``Context`` or ``RequestContext`` that is used to
   render a template.

   The current application can also be specified manually as an argument
   to the :func:`django.core.urlresolvers.reverse` function.

3. If there is no current application. Django looks for a default
   application instance. The default application instance is the instance
   that has an :term:`instance namespace` matching the :term:`application
   namespace` (in this example, an instance of the ``myapp`` called
   ``'myapp'``).

4. If there is no default application instance, Django will pick the last
   deployed instance of the application, whatever its instance name may be.

5. If the provided namespace doesn't match an :term:`application namespace` in
   step 1, Django will attempt a direct lookup of the namespace as an
   :term:`instance namespace`.

If there are nested namespaces, these steps are repeated for each part of the
namespace until only the view name is unresolved. The view name will then be
resolved into a URL in the namespace that has been found.

Example
~~~~~~~

To show this resolution strategy in action, consider an example of two instances
of ``myapp``: one called ``'foo'``, and one called ``'bar'``. ``myapp`` has a
main index page with a URL named ``'index'``. Using this setup, the following
lookups are possible:

* If one of the instances is current - say, if we were rendering a utility page
  in the instance ``'bar'`` - ``'myapp:index'`` will resolve to the index page
  of the instance ``'bar'``.

* If there is no current instance - say, if we were rendering a page
  somewhere else on the site - ``'myapp:index'`` will resolve to the last
  registered instance of ``myapp``. Since there is no default instance,
  the last instance of ``myapp`` that is registered will be used. This could
  be ``'foo'`` or ``'bar'``, depending on the order they are introduced into the
  urlpatterns of the project.

* ``'foo:index'`` will always resolve to the index page of the instance
  ``'foo'``.

If there was also a default instance - i.e., an instance named ``'myapp'`` - the
following would happen:

* If one of the instances is current - say, if we were rendering a utility page
  in the instance ``'bar'`` - ``'myapp:index'`` will resolve to the index page
  of the instance ``'bar'``.

* If there is no current instance - say, if we were rendering a page somewhere
  else on the site - ``'myapp:index'`` will resolve to the index page of the
  default instance.

* ``'foo:index'`` will again resolve to the index page of the instance
  ``'foo'``.

.. _namespaces-and-include:

URL namespaces and included URLconfs
------------------------------------

URL namespaces of included URLconfs can be specified in two ways.

Firstly, you can provide the :term:`application <application namespace>` and
:term:`instance <instance namespace>` namespaces as arguments to
:func:`django.conf.urls.include()` when you construct your URL patterns. For
example,::

    (r'^help/', include('apps.help.urls', namespace='foo', app_name='bar')),

This will include the URLs defined in ``apps.help.urls`` into the
:term:`application namespace` ``'bar'``, with the :term:`instance namespace`
``'foo'``.

Secondly, you can include an object that contains embedded namespace data. If
you ``include()`` an object as returned by :func:`~django.conf.urls.patterns`,
the URLs contained in that object will be added to the global namespace.
However, you can also ``include()`` a 3-tuple containing::

    (<patterns object>, <application namespace>, <instance namespace>)

For example::

    help_patterns = patterns('',
        url(r'^basic/$', 'apps.help.views.views.basic'),
        url(r'^advanced/$', 'apps.help.views.views.advanced'),
    )

    (r'^help/', include(help_patterns, 'bar', 'foo')),

This will include the nominated URL patterns into the given application and
instance namespace.

For example, the Django Admin is deployed as instances of
:class:`~django.contrib.admin.AdminSite`.  ``AdminSite`` objects have a ``urls``
attribute: A 3-tuple that contains all the patterns in the corresponding admin
site, plus the application namespace ``'admin'``, and the name of the admin
instance. It is this ``urls`` attribute that you ``include()`` into your
projects ``urlpatterns`` when you deploy an Admin instance.
