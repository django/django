==========================
Generic comment moderation
==========================

.. module:: django.contrib.comments.moderation
   :synopsis: Support for automatic comment moderation.

Django's bundled comments application is extremely useful on its own,
but the amount of comment spam circulating on the Web today
essentially makes it necessary to have some sort of automatic
moderation system in place for any application which makes use of
comments. To make this easier to handle in a consistent fashion,
``django.contrib.comments.moderation`` provides a generic, extensible
comment-moderation system which can be applied to any model or set of
models which want to make use of Django's comment system.


Overview
========

The entire system is contained within ``django.contrib.comments.moderation``,
and uses a two-step process to enable moderation for any given model:

1. A subclass of :class:`CommentModerator`
   is defined which specifies the moderation options the model wants to
   enable.

2. The model is registered with the moderation system, passing in the
   model class and the class which specifies its moderation options.

A simple example is the best illustration of this. Suppose we have the
following model, which would represent entries in a Weblog::

    from django.db import models

    class Entry(models.Model):
        title = models.CharField(maxlength=250)
        body = models.TextField()
        pub_date = models.DateField()
        enable_comments = models.BooleanField()

Now, suppose that we want the following steps to be applied whenever a
new comment is posted on an ``Entry``:

1. If the ``Entry``'s ``enable_comments`` field is ``False``, the
   comment will simply be disallowed (i.e., immediately deleted).

2. If the ``enable_comments`` field is ``True``, the comment will be
   allowed to save.

3. Once the comment is saved, an email should be sent to site staff
   notifying them of the new comment.

Accomplishing this is fairly straightforward and requires very little
code::

    from django.contrib.comments.moderation import CommentModerator, moderator

    class EntryModerator(CommentModerator):
        email_notification = True
        enable_field = 'enable_comments'

    moderator.register(Entry, EntryModerator)

The :class:`CommentModerator` class pre-defines a number of useful moderation
options which subclasses can enable or disable as desired, and ``moderator``
knows how to work with them to determine whether to allow a comment, whether
to moderate a comment which will be allowed to post, and whether to email
notifications of new comments.

Built-in moderation options
---------------------------

.. class:: CommentModerator

    Most common comment-moderation needs can be handled by subclassing
    :class:`CommentModerator` and
    changing the values of pre-defined attributes; the full range of built-in
    options is as follows.

    .. attribute:: auto_close_field

        If this is set to the name of a
        :class:`~django.db.models.DateField` or
        :class:`~django.db.models.DateTimeField` on the model for which
        comments are being moderated, new comments for objects of that model
        will be disallowed (immediately deleted) when a certain number of days
        have passed after the date specified in that field. Must be
        used in conjunction with :attr:`close_after`, which specifies the
        number of days past which comments should be
        disallowed. Default value is ``None``.

    .. attribute:: auto_moderate_field

        Like :attr:`auto_close_field`, but instead of outright deleting
        new comments when the requisite number of days have elapsed,
        it will simply set the ``is_public`` field of new comments to
        ``False`` before saving them. Must be used in conjunction with
        :attr:`moderate_after`, which specifies the number of days past
        which comments should be moderated. Default value is ``None``.

    .. attribute:: close_after

        If :attr:`auto_close_field` is used, this must specify the number
        of days past the value of the field specified by
        :attr:`auto_close_field` after which new comments for an object
        should be disallowed. Allowed values are ``None``, 0 (which disallows
        comments immediately), or any positive integer. Default value is
        ``None``.

    .. attribute:: email_notification

        If ``True``, any new comment on an object of this model which
        survives moderation (i.e., is not deleted) will generate an
        email to site staff. Default value is ``False``.

    .. attribute:: enable_field

        If this is set to the name of a
        :class:`~django.db.models.BooleanField` on the model
        for which comments are being moderated, new comments on
        objects of that model will be disallowed (immediately deleted)
        whenever the value of that field is ``False`` on the object
        the comment would be attached to. Default value is ``None``.

    .. attribute:: moderate_after

        If :attr:`auto_moderate_field` is used, this must specify the number
        of days past the value of the field specified by
        :attr:`auto_moderate_field` after which new comments for an object
        should be marked non-public. Allowed values are ``None``, 0 (which
        moderates comments immediately), or any positive integer. Default
        value is ``None``.

Simply subclassing :class:`CommentModerator` and changing the values of these
options will automatically enable the various moderation methods for any
models registered using the subclass.

Adding custom moderation methods
--------------------------------

For situations where the built-in options listed above are not
sufficient, subclasses of :class:`CommentModerator` can also override
the methods which actually perform the moderation, and apply any logic
they desire.  :class:`CommentModerator` defines three methods which
determine how moderation will take place; each method will be called
by the moderation system and passed two arguments: ``comment``, which
is the new comment being posted, ``content_object``, which is the
object the comment will be attached to, and ``request``, which is the
:class:`~django.http.HttpRequest` in which the comment is being submitted:

.. method:: CommentModerator.allow(comment, content_object, request)

    Should return ``True`` if the comment should be allowed to
    post on the content object, and ``False`` otherwise (in which
    case the comment will be immediately deleted).

.. method:: CommentModerator.email(comment, content_object, request)

    If email notification of the new comment should be sent to
    site staff or moderators, this method is responsible for
    sending the email.

.. method:: CommentModerator.moderate(comment, content_object, request)

    Should return ``True`` if the comment should be moderated (in
    which case its ``is_public`` field will be set to ``False``
    before saving), and ``False`` otherwise (in which case the
    ``is_public`` field will not be changed).


Registering models for moderation
---------------------------------

The moderation system, represented by
``django.contrib.comments.moderation.moderator`` is an instance of the class
:class:`Moderator`, which allows registration and "unregistration" of models
via two methods:

.. function:: moderator.register(model_or_iterable, moderation_class)

    Takes two arguments: the first should be either a model class
    or list of model classes, and the second should be a subclass
    of ``CommentModerator``, and register the model or models to
    be moderated using the options defined in the
    ``CommentModerator`` subclass. If any of the models are
    already registered for moderation, the exception
    ``AlreadyModerated`` will be raised.

.. function:: moderator.unregister(model_or_iterable)

    Takes one argument: a model class or list of model classes,
    and removes the model or models from the set of models which
    are being moderated. If any of the models are not currently
    being moderated, the exception ``NotModerated`` will be raised.


Customizing the moderation system
---------------------------------

Most use cases will work easily with simple subclassing of
:class:`CommentModerator` and registration with the provided
:class:`Moderator` instance, but customization of global moderation behavior
can be achieved by subclassing :class:`Moderator` and instead registering
models with an instance of the subclass.

.. class:: Moderator

    In addition to the :func:`moderator.register` and
    :func:`moderator.unregister` methods detailed above, the following methods
    on :class:`Moderator` can be overridden to achieve customized behavior:

    .. method:: connect

        Determines how moderation is set up globally. The base
        implementation in
        :class:`Moderator` does this by
        attaching listeners to the :data:`~django.contrib.comments.signals.comment_will_be_posted`
        and :data:`~django.contrib.comments.signals.comment_was_posted` signals from the
        comment models.

    .. method:: pre_save_moderation(sender, comment, request, **kwargs)

        In the base implementation, applies all pre-save moderation
        steps (such as determining whether the comment needs to be
        deleted, or whether it needs to be marked as non-public or
        generate an email).

    .. method:: post_save_moderation(sender, comment, request, **kwargs)

        In the base implementation, applies all post-save moderation
        steps (currently this consists entirely of deleting comments
        which were disallowed).
