====================
Single object mixins
====================

SingleObjectMixin
-----------------

.. class:: django.views.generic.detail.SingleObjectMixin

    Provides a mechanism for looking up an object associated with the
    current HTTP request.

    **Methods and Attributes**

    .. attribute:: model

        The model that this view will display data for. Specifying ``model
        = Foo`` is effectively the same as specifying ``queryset =
        Foo.objects.all()``.

    .. attribute:: queryset

        A ``QuerySet`` that represents the objects. If provided, the value of
        ``queryset`` supersedes the value provided for :attr:`model`.

    .. attribute:: slug_field

        The name of the field on the model that contains the slug. By default,
        ``slug_field`` is ``'slug'``.

    .. attribute:: slug_url_kwarg

        .. versionadded:: 1.4

        The name of the URLConf keyword argument that contains the slug. By
        default, ``slug_url_kwarg`` is ``'slug'``.

    .. attribute:: pk_url_kwarg

        .. versionadded:: 1.4

        The name of the URLConf keyword argument that contains the primary key.
        By default, ``pk_url_kwarg`` is ``'pk'``.

    .. attribute:: context_object_name

        Designates the name of the variable to use in the context.

    .. method:: get_object(queryset=None)

        Returns the single object that this view will display. If
        ``queryset`` is provided, that queryset will be used as the
        source of objects; otherwise, :meth:`get_queryset` will be used.
        ``get_object()`` looks for a :attr:`pk_url_kwarg` argument in the
        arguments to the view; if this argument is found, this method performs
        a primary-key based lookup using that value. If this argument is not
        found, it looks for a :attr:`slug_url_kwarg` argument, and performs a
        slug lookup using the :attr:`slug_field`.

    .. method:: get_queryset()

        Returns the queryset that will be used to retrieve the object that
        this view will display. By default, :meth:`get_queryset` returns the
        value of the :attr:`queryset` attribute if it is set, otherwise
        it constructs a :class:`~django.db.models.query.QuerySet` by calling
        the `all()` method on the :attr:`model` attribute's default manager.

    .. method:: get_context_object_name(obj)

        Return the context variable name that will be used to contain the
        data that this view is manipulating. If :attr:`context_object_name` is
        not set, the context name will be constructed from the ``object_name``
        of the model that the queryset is composed from. For example, the model
        ``Article`` would have context object named ``'article'``.

    .. method:: get_context_data(**kwargs)

        Returns context data for displaying the list of objects.

    .. method:: get_slug_field()

        Returns the name of a slug field to be used to look up by slug. By
        default this simply returns the value of :attr:`slug_field`.

    **Context**

    * ``object``: The object that this view is displaying. If
      ``context_object_name`` is specified, that variable will also be
      set in the context, with the same value as ``object``.

SingleObjectTemplateResponseMixin
---------------------------------

.. class:: django.views.generic.detail.SingleObjectTemplateResponseMixin

    A mixin class that performs template-based response rendering for views
    that operate upon a single object instance. Requires that the view it is
    mixed with provides ``self.object``, the object instance that the view is
    operating on. ``self.object`` will usually be, but is not required to be,
    an instance of a Django model. It may be ``None`` if the view is in the
    process of constructing a new instance.

    **Extends**

    * :class:`~django.views.generic.base.TemplateResponseMixin`

    **Methods and Attributes**

    .. attribute:: template_name_field

        The field on the current object instance that can be used to determine
        the name of a candidate template. If either ``template_name_field``
        itself or the value of the ``template_name_field`` on the current
        object instance is ``None``, the object will not be used for a
        candidate template name.

    .. attribute:: template_name_suffix

        The suffix to append to the auto-generated candidate template name.
        Default suffix is ``_detail``.

    .. method:: get_template_names()

        Returns a list of candidate template names. Returns the following list:

        * the value of ``template_name`` on the view (if provided)
        * the contents of the ``template_name_field`` field on the
          object instance that the view is operating upon (if available)
        * ``<app_label>/<object_name><template_name_suffix>.html``
