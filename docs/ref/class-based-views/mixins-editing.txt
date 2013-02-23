==============
Editing mixins
==============

The following mixins are used to construct Django's editing views:

* :class:`django.views.generic.edit.FormMixin`
* :class:`django.views.generic.edit.ModelFormMixin`
* :class:`django.views.generic.edit.ProcessFormView`
* :class:`django.views.generic.edit.DeletionMixin`

.. note::

    Examples of how these are combined into editing views can be found at
    the documentation on ``Generic editing views``.

FormMixin
---------

.. class:: django.views.generic.edit.FormMixin

    A mixin class that provides facilities for creating and displaying forms.

    **Methods and Attributes**

    .. attribute:: initial

        A dictionary containing initial data for the form.

    .. attribute:: form_class

        The form class to instantiate.

    .. attribute:: success_url

        The URL to redirect to when the form is successfully processed.

    .. method:: get_initial()

        Retrieve initial data for the form. By default, returns a copy of
        :attr:`~django.views.generic.edit.FormMixin.initial`.

        .. versionchanged:: 1.4
            In Django 1.3, this method was returning the
            :attr:`~django.views.generic.edit.FormMixin.initial` class variable
            itself.

    .. method:: get_form_class()

        Retrieve the form class to instantiate. By default
        :attr:`.form_class`.

    .. method:: get_form(form_class)

        Instantiate an instance of ``form_class`` using
        :meth:`~django.views.generic.edit.FormMixin.get_form_kwargs`.

    .. method:: get_form_kwargs()

        Build the keyword arguments required to instantiate the form.

        The ``initial`` argument is set to :meth:`.get_initial`. If the
        request is a ``POST`` or ``PUT``, the request data (``request.POST``
        and ``request.FILES``) will also be provided.

    .. method:: get_success_url()

        Determine the URL to redirect to when the form is successfully
        validated. Returns
        :attr:`~django.views.generic.edit.FormMixin.success_url` by default.

    .. method:: form_valid(form)

        Redirects to
        :meth:`~django.views.generic.edit.FormMixin.get_success_url`.

    .. method:: form_invalid(form)

        Renders a response, providing the invalid form as context.

    .. method:: get_context_data(**kwargs)

        Populates a context containing the contents of ``kwargs``.

    **Context**

    * ``form``: The form instance that was generated for the view.

    .. note::

        Views mixing ``FormMixin`` must provide an implementation of
        :meth:`form_valid` and :meth:`form_invalid`.


ModelFormMixin
--------------

.. class:: django.views.generic.edit.ModelFormMixin

    A form mixin that works on ``ModelForms``, rather than a standalone form.

    Since this is a subclass of
    :class:`~django.views.generic.detail.SingleObjectMixin`, instances of this
    mixin have access to the
    :attr:`~django.views.generic.detail.SingleObjectMixin.model` and
    :attr:`~django.views.generic.detail.SingleObjectMixin.queryset` attributes,
    describing the type of object that the ``ModelForm`` is manipulating. The
    view also provides ``self.object``, the instance being manipulated. If the
    instance is being created, ``self.object`` will be ``None``.

    **Mixins**

    * :class:`django.views.generic.edit.FormMixin`
    * :class:`django.views.generic.detail.SingleObjectMixin`

    **Methods and Attributes**

    .. attribute:: model

        A model class. Can be explicitly provided, otherwise will be determined
        by examining ``self.object`` or
        :attr:`~django.views.generic.detail.SingleObjectMixin.queryset`.

    .. attribute:: success_url

        The URL to redirect to when the form is successfully processed.

        ``success_url`` may contain dictionary string formatting, which
        will be interpolated against the object's field attributes. For
        example, you could use ``success_url="/polls/%(slug)s/"`` to
        redirect to a URL composed out of the ``slug`` field on a model.

    .. method:: get_form_class()

        Retrieve the form class to instantiate. If
        :attr:`~django.views.generic.edit.FormMixin.form_class` is provided,
        that class will be used. Otherwise, a ``ModelForm`` will be
        instantiated using the model associated with the
        :attr:`~django.views.generic.detail.SingleObjectMixin.queryset`, or
        with the :attr:`~django.views.generic.detail.SingleObjectMixin.model`,
        depending on which attribute is provided.

    .. method:: get_form_kwargs()

        Add the current instance (``self.object``) to the standard
        :meth:`~django.views.generic.edit.FormMixin.get_form_kwargs`.

    .. method:: get_success_url()

        Determine the URL to redirect to when the form is successfully
        validated. Returns
        :attr:`django.views.generic.edit.ModelFormMixin.success_url` if it is
        provided; otherwise, attempts to use the ``get_absolute_url()`` of the
        object.

    .. method:: form_valid(form)

        Saves the form instance, sets the current object for the view, and
        redirects to
        :meth:`~django.views.generic.edit.FormMixin.get_success_url`.

    .. method:: form_invalid()

        Renders a response, providing the invalid form as context.


ProcessFormView
---------------

.. class:: django.views.generic.edit.ProcessFormView

    A mixin that provides basic HTTP GET and POST workflow.

    .. note::

        This is named 'ProcessFormView' and inherits directly from
        :class:`django.views.generic.base.View`, but breaks if used
        independently, so it is more of a mixin.

    **Extends**

    * :class:`django.views.generic.base.View`

    **Methods and Attributes**

    .. method:: get(request, *args, **kwargs)

        Constructs a form, then renders a response using a context that
        contains that form.

    .. method:: post(request, *args, **kwargs)

        Constructs a form, checks the form for validity, and handles it
        accordingly.

    The PUT action is also handled, as an analog of POST.

.. class:: django.views.generic.edit.DeletionMixin

    Enables handling of the ``DELETE`` http action.

    **Methods and Attributes**

    .. attribute:: success_url

        The url to redirect to when the nominated object has been
        successfully deleted.

    .. method:: get_success_url()

        Returns the url to redirect to when the nominated object has been
        successfully deleted. Returns
        :attr:`~django.views.generic.edit.DeletionMixin.success_url` by
        default.
