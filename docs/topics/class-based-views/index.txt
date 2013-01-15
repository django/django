=================
Class-based views
=================

A view is a callable which takes a request and returns a
response. This can be more than just a function, and Django provides
an example of some classes which can be used as views. These allow you
to structure your views and reuse code by harnessing inheritance and
mixins. There are also some generic views for simple tasks which we'll
get to later, but you may want to design your own structure of
reusable views which suits your use case. For full details, see the
:doc:`class-based views reference documentation</ref/class-based-views/index>`.

.. toctree::
   :maxdepth: 1

   generic-display
   generic-editing
   mixins

Basic examples
==============

Django provides base view classes which will suit a wide range of applications.
All views inherit from the :class:`~django.views.generic.base.View` class, which
handles linking the view in to the URLs, HTTP method dispatching and other
simple features. :class:`~django.views.generic.base.RedirectView` is for a
simple HTTP redirect, and :class:`~django.views.generic.base.TemplateView`
extends the base class to make it also render a template.


Simple usage in your URLconf
============================

The simplest way to use generic views is to create them directly in your
URLconf. If you're only changing a few simple attributes on a class-based view,
you can simply pass them into the
:meth:`~django.views.generic.base.View.as_view` method call itself::

    from django.conf.urls import patterns
    from django.views.generic import TemplateView

    urlpatterns = patterns('',
        (r'^about/', TemplateView.as_view(template_name="about.html")),
    )

Any arguments passed to :meth:`~django.views.generic.base.View.as_view` will
override attributes set on the class. In this example, we set ``template_name``
on the ``TemplateView``. A similar overriding pattern can be used for the
``url`` attribute on :class:`~django.views.generic.base.RedirectView`.


Subclassing generic views
=========================

The second, more powerful way to use generic views is to inherit from an
existing view and override attributes (such as the ``template_name``) or
methods (such as ``get_context_data``) in your subclass to provide new values
or methods. Consider, for example, a view that just displays one template,
``about.html``. Django has a generic view to do this -
:class:`~django.views.generic.base.TemplateView` - so we can just subclass it,
and override the template name::

    # some_app/views.py
    from django.views.generic import TemplateView

    class AboutView(TemplateView):
        template_name = "about.html"

Then we just need to add this new view into our URLconf.
`~django.views.generic.base.TemplateView` is a class, not a function, so we
point the URL to the :meth:`~django.views.generic.base.View.as_view` class
method instead, which provides a function-like entry to class-based views::

    # urls.py
    from django.conf.urls import patterns
    from some_app.views import AboutView

    urlpatterns = patterns('',
        (r'^about/', AboutView.as_view()),
    )


For more information on how to use the built in generic views, consult the next
topic on :doc:`generic class based views</topics/class-based-views/generic-display>`.

.. _supporting-other-http-methods:

Supporting other HTTP methods
-----------------------------

Suppose somebody wants to access our book library over HTTP using the views
as an API. The API client would connect every now and then and download book
data for the books published since last visit. But if no new books appeared
since then, it is a waste of CPU time and bandwidth to fetch the books from the
database, render a full response and send it to the client. It might be
preferable to ask the API when the most recent book was published.

We map the URL to book list view in the URLconf::

    from django.conf.urls import patterns
    from books.views import BookListView

    urlpatterns = patterns('',
        (r'^books/$', BookListView.as_view()),
    )

And the view::

    from django.http import HttpResponse
    from django.views.generic import ListView
    from books.models import Book

    class BookListView(ListView):
        model = Book

        def head(self, *args, **kwargs):
            last_book = self.get_queryset().latest('publication_date')
            response = HttpResponse('')
            # RFC 1123 date format
            response['Last-Modified'] = last_book.publication_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
            return response

If the view is accessed from a ``GET`` request, a plain-and-simple object
list is returned in the response (using ``book_list.html`` template). But if
the client issues a ``HEAD`` request, the response has an empty body and
the ``Last-Modified`` header indicates when the most recent book was published.
Based on this information, the client may or may not download the full object
list.

Decorating class-based views
============================

.. highlightlang:: python

Since class-based views aren't functions, decorating them works differently
depending on if you're using ``as_view`` or creating a subclass.

Decorating in URLconf
---------------------

The simplest way of decorating class-based views is to decorate the
result of the :meth:`~django.views.generic.base.View.as_view` method.
The easiest place to do this is in the URLconf where you deploy your view::

    from django.contrib.auth.decorators import login_required, permission_required
    from django.views.generic import TemplateView

    from .views import VoteView

    urlpatterns = patterns('',
        (r'^about/', login_required(TemplateView.as_view(template_name="secret.html"))),
        (r'^vote/', permission_required('polls.can_vote')(VoteView.as_view())),
    )

This approach applies the decorator on a per-instance basis. If you
want every instance of a view to be decorated, you need to take a
different approach.

.. _decorating-class-based-views:

Decorating the class
--------------------

To decorate every instance of a class-based view, you need to decorate
the class definition itself. To do this you apply the decorator to the
:meth:`~django.views.generic.base.View.dispatch` method of the class.

A method on a class isn't quite the same as a standalone function, so
you can't just apply a function decorator to the method -- you need to
transform it into a method decorator first. The ``method_decorator``
decorator transforms a function decorator into a method decorator so
that it can be used on an instance method. For example::

    from django.contrib.auth.decorators import login_required
    from django.utils.decorators import method_decorator
    from django.views.generic import TemplateView

    class ProtectedView(TemplateView):
        template_name = 'secret.html'

        @method_decorator(login_required)
        def dispatch(self, *args, **kwargs):
            return super(ProtectedView, self).dispatch(*args, **kwargs)

In this example, every instance of ``ProtectedView`` will have
login protection.

.. note::

    ``method_decorator`` passes ``*args`` and ``**kwargs``
    as parameters to the decorated method on the class. If your method
    does not accept a compatible set of parameters it will raise a
    ``TypeError`` exception.
