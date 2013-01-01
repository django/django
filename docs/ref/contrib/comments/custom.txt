==================================
Customizing the comments framework
==================================

.. currentmodule:: django.contrib.comments

If the built-in comment framework doesn't quite fit your needs, you can extend
the comment app's behavior to add custom data and logic. The comments framework
lets you extend the built-in comment model, the built-in comment form, and the
various comment views.

The :setting:`COMMENTS_APP` setting is where this customization begins. Set
:setting:`COMMENTS_APP` to the name of the app you'd like to use to provide
custom behavior. You'll use the same syntax as you'd use for
:setting:`INSTALLED_APPS`, and the app given must also be in the
:setting:`INSTALLED_APPS` list.

For example, if you wanted to use an app named ``my_comment_app``, your
settings file would contain::

    INSTALLED_APPS = [
        ...
        'my_comment_app',
        ...
    ]

    COMMENTS_APP = 'my_comment_app'

The app named in :setting:`COMMENTS_APP` provides its custom behavior by
defining some module-level functions in the app's ``__init__.py``. The
:ref:`complete list of these functions <custom-comment-app-api>` can be found
below, but first let's look at a quick example.

An example custom comments app
==============================

One of the most common types of customization is modifying the set of fields
provided on the built-in comment model. For example, some sites that allow
comments want the commentator to provide a title for their comment; the built-in
comment model has no field for that title.

To make this kind of customization, we'll need to do three things:

#. Create a custom comment :class:`~django.db.models.Model` that adds on the
   "title" field.

#. Create a custom comment :class:`~django.forms.Form` that also adds this
   "title" field.

#. Inform Django of these objects by defining a few functions in a
   custom :setting:`COMMENTS_APP`.

So, carrying on the example above, we're dealing with a typical app structure in
the ``my_comment_app`` directory::

    my_comment_app/
        __init__.py
        models.py
        forms.py

In the ``models.py`` we'll define a ``CommentWithTitle`` model::

    from django.db import models
    from django.contrib.comments.models import Comment

    class CommentWithTitle(Comment):
        title = models.CharField(max_length=300)

Most custom comment models will subclass the
:class:`~django.contrib.comments.models.Comment` model. However,
if you want to substantially remove or change the fields available in the
:class:`~django.contrib.comments.models.Comment` model, but don't want to
rewrite the templates, you could try subclassing from
``BaseCommentAbstractModel``.

Next, we'll define a custom comment form in ``forms.py``. This is a little more
tricky: we have to both create a form and override
``CommentForm.get_comment_model()`` and
``CommentForm.get_comment_create_data()`` to return deal with our custom title
field::

    from django import forms
    from django.contrib.comments.forms import CommentForm
    from my_comment_app.models import CommentWithTitle

    class CommentFormWithTitle(CommentForm):
        title = forms.CharField(max_length=300)

        def get_comment_model(self):
            # Use our custom comment model instead of the built-in one.
            return CommentWithTitle

        def get_comment_create_data(self):
            # Use the data of the superclass, and add in the title field
            data = super(CommentFormWithTitle, self).get_comment_create_data()
            data['title'] = self.cleaned_data['title']
            return data

Django provides a couple of "helper" classes to make writing certain types of
custom comment forms easier; see :mod:`django.contrib.comments.forms` for
more.

Finally, we'll define a couple of methods in ``my_comment_app/__init__.py`` to
point Django at these classes we've created::

    from my_comment_app.models import CommentWithTitle
    from my_comment_app.forms import CommentFormWithTitle

    def get_model():
        return CommentWithTitle

    def get_form():
        return CommentFormWithTitle


.. warning::

    Be careful not to create cyclic imports in your custom comments app.
    If you feel your comment configuration isn't being used as defined --
    for example, if your comment moderation policy isn't being applied --
    you may have a cyclic import problem.

    If you are having unexplained problems with comments behavior, check
    if your custom comments application imports (even indirectly)
    any module that itself imports Django's comments module.

The above process should take care of most common situations. For more
advanced usage, there are additional methods you can define. Those are
explained in the next section.

.. _custom-comment-app-api:

Custom comment app API
======================

The :mod:`django.contrib.comments` app defines the following methods; any
custom comment app must define at least one of them. All are optional,
however.

.. function:: get_model()

    Return the :class:`~django.db.models.Model` class to use for comments. This
    model should inherit from
    ``django.contrib.comments.models.BaseCommentAbstractModel``, which
    defines necessary core fields.

    The default implementation returns
    :class:`django.contrib.comments.models.Comment`.

.. function:: get_form()

    Return the :class:`~django.forms.Form` class you want to use for
    creating, validating, and saving your comment model.  Your custom
    comment form should accept an additional first argument,
    ``target_object``, which is the object the comment will be
    attached to.

    The default implementation returns
    :class:`django.contrib.comments.forms.CommentForm`.

    .. note::

        The default comment form also includes a number of unobtrusive
        spam-prevention features (see
        :ref:`notes-on-the-comment-form`).  If replacing it with your
        own form, you may want to look at the source code for the
        built-in form and consider incorporating similar features.

.. function:: get_form_target()

    Return the URL for POSTing comments. This will be the ``<form action>``
    attribute when rendering your comment form.

    The default implementation returns a reverse-resolved URL pointing
    to the ``post_comment()`` view.

    .. note::

        If you provide a custom comment model and/or form, but you
        want to use the default ``post_comment()`` view, you will
        need to be aware that it requires the model and form to have
        certain additional attributes and methods: see the
        ``django.contrib.comments.views.post_comment()`` view for details.

.. function:: get_flag_url()

    Return the URL for the "flag this comment" view.

    The default implementation returns a reverse-resolved URL pointing
    to the ``django.contrib.comments.views.moderation.flag()`` view.

.. function:: get_delete_url()

    Return the URL for the "delete this comment" view.

    The default implementation returns a reverse-resolved URL pointing
    to the ``django.contrib.comments.views.moderation.delete()`` view.

.. function:: get_approve_url()

    Return the URL for the "approve this comment from moderation" view.

    The default implementation returns a reverse-resolved URL pointing
    to the ``django.contrib.comments.views.moderation.approve()`` view.
