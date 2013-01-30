=============
Simple mixins
=============

ContextMixin
------------

.. class:: django.views.generic.base.ContextMixin

    .. versionadded:: 1.5

    **Methods**

    .. method:: get_context_data(**kwargs)

        Returns a dictionary representing the template context. The keyword
        arguments provided will make up the returned context. Example usage::

            def get_context_data(self, **kwargs):
                context = super(RandomNumberView, self).get_context_data(**kwargs)
                context['number'] = random.randrange(1, 100)
                return context

        The template context of all class-based generic views include a
        ``view`` variable that points to the ``View`` instance.

        .. admonition:: Use ``alters_data`` where appropriate

            Note that having the view instance in the template context may
            expose potentially hazardous methods to template authors.  To
            prevent methods like this from being called in the template, set
            ``alters_data=True`` on those methods.  For more information, read
            the documentation on :ref:`rendering a template context
            <alters-data-description>`.

TemplateResponseMixin
---------------------

.. class:: django.views.generic.base.TemplateResponseMixin

    Provides a mechanism to construct a
    :class:`~django.template.response.TemplateResponse`, given
    suitable context. The template to use is configurable and can be
    further customized by subclasses.

    **Attributes**

    .. attribute:: template_name

        The full name of a template to use as defined by a string. Not defining
        a ``template_name`` will raise a
        :class:`django.core.exceptions.ImproperlyConfigured` exception.

    .. attribute:: response_class

        The response class to be returned by ``render_to_response`` method.
        Default is
        :class:`TemplateResponse <django.template.response.TemplateResponse>`.
        The template and context of ``TemplateResponse`` instances can be
        altered later (e.g. in
        :ref:`template response middleware <template-response-middleware>`).

        If you need custom template loading or custom context object
        instantiation, create a ``TemplateResponse`` subclass and assign it to
        ``response_class``.

    .. attribute:: content_type

        .. versionadded:: 1.5
            The ``content_type`` attribute was added.

        The content type to use for the response. ``content_type`` is passed
        as a keyword argument to ``response_class``. Default is ``None`` --
        meaning that Django uses :setting:`DEFAULT_CONTENT_TYPE`.

    **Methods**

    .. method:: render_to_response(context, **response_kwargs)

        Returns a ``self.response_class`` instance.

        If any keyword arguments are provided, they will be passed to the
        constructor of the response class.

        Calls :meth:`get_template_names()` to obtain the list of template names
        that will be searched looking for an existent template.

    .. method:: get_template_names()

        Returns a list of template names to search for when rendering the
        template.

        If :attr:`template_name` is specified, the default implementation will
        return a list containing :attr:`template_name` (if it is specified).
