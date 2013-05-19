================================
Signals sent by the comments app
================================

.. module:: django.contrib.comments.signals
   :synopsis: Signals sent by the comment module.

.. warning::

    Django's comment framework has been deprecated and is no longer supported.
    Most users will be better served with a custom solution, or a hosted
    product like Disqus__.

    The code formerly known as ``django.contrib.comments`` is `still available
    in an external repository`__.

    __ https://disqus.com/
    __ https://github.com/django/django-contrib-comments

The comment app sends a series of :doc:`signals </topics/signals>` to allow for
comment moderation and similar activities. See :doc:`the introduction to signals
</topics/signals>` for information about how to register for and receive these
signals.

comment_will_be_posted
======================

.. data:: django.contrib.comments.signals.comment_will_be_posted
   :module:

Sent just before a comment will be saved, after it's been sanity checked and
submitted. This can be used to modify the comment (in place) with posting
details or other such actions.

If any receiver returns ``False`` the comment will be discarded and a 400
response will be returned.

This signal is sent at more or less the same time (just before, actually) as the
``Comment`` object's :data:`~django.db.models.signals.pre_save` signal.

Arguments sent with this signal:

``sender``
    The comment model.

``comment``
    The comment instance about to be posted. Note that it won't have been
    saved into the database yet, so it won't have a primary key, and any
    relations might not work correctly yet.

``request``
    The :class:`~django.http.HttpRequest` that posted the comment.

comment_was_posted
==================

.. data:: django.contrib.comments.signals.comment_was_posted
   :module:

Sent just after the comment is saved.

Arguments sent with this signal:

``sender``
    The comment model.

``comment``
    The comment instance that was posted. Note that it will have already
    been saved, so if you modify it you'll need to call
    :meth:`~django.db.models.Model.save` again.

``request``
    The :class:`~django.http.HttpRequest` that posted the comment.

comment_was_flagged
===================

.. data:: django.contrib.comments.signals.comment_was_flagged
   :module:

Sent after a comment was "flagged" in some way. Check the flag to see if this
was a user requesting removal of a comment, a moderator approving/removing a
comment, or some other custom user flag.

Arguments sent with this signal:

``sender``
    The comment model.

``comment``
    The comment instance that was posted. Note that it will have already
    been saved, so if you modify it you'll need to call
    :meth:`~django.db.models.Model.save` again.

``flag``
    The ``django.contrib.comments.models.CommentFlag`` that's been attached to
    the comment.

``created``
    ``True`` if this is a new flag; ``False`` if it's a duplicate flag.

``request``
    The :class:`~django.http.HttpRequest` that posted the comment.
