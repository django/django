=================
Class-based views
=================

Class-based views API reference. For introductory material, see
:doc:`/topics/class-based-views/index`.

.. toctree::
   :maxdepth: 3

   base
   generic-display
   generic-editing
   generic-date-based
   mixins
   flattened-index

Specification
-------------

Each request served by a class-based view has an independent state; therefore,
it is safe to store state variables on the instance (i.e., ``self.foo = 3`` is
a thread-safe operation).

A class-based view is deployed into a URL pattern using the
:meth:`~django.views.generic.base.View.as_view()` classmethod::

    urlpatterns = patterns('',
        (r'^view/$', MyView.as_view(size=42)),
    )

.. admonition:: Thread safety with view arguments

    Arguments passed to a view are shared between every instance of a view.
    This means that you shoudn't use a list, dictionary, or any other
    mutable object as an argument to a view. If you do and the shared object
    is modified, the actions of one user visiting your view could have an
    effect on subsequent users visiting the same view.

Arguments passed into :meth:`~django.views.generic.base.View.as_view()` will
be assigned onto the instance that is used to service a request. Using the
previous example, this means that every request on ``MyView`` is able to use
``self.size``. Arguments must correspond to attributes that already exist on
the class (return ``True`` on a ``hasattr`` check).

Base vs Generic views
---------------------

Base class-based views can be thought of as *parent* views, which can be
used by themselves or inherited from. They may not provide all the
capabilities required for projects, in which case there are Mixins which
extend what base views can do.

Django’s generic views are built off of those base views, and were developed
as a shortcut for common usage patterns such as displaying the details of an
object. They take certain common idioms and patterns found in view
development and abstract them so that you can quickly write common views of
data without having to repeat yourself.

Most generic views require the ``queryset`` key, which is a ``QuerySet``
instance; see :doc:`/topics/db/queries` for more information about ``QuerySet``
objects.
