================
Comment settings
================

These settings configure the behavior of the comments framework:

.. setting:: COMMENTS_HIDE_REMOVED

COMMENTS_HIDE_REMOVED
---------------------

If ``True`` (default), removed comments will be excluded from comment
lists/counts (as taken from template tags). Otherwise, the template author is
responsible for some sort of a "this comment has been removed by the site staff"
message.

.. setting:: COMMENT_MAX_LENGTH

COMMENT_MAX_LENGTH
------------------

The maximum length of the comment field, in characters. Comments longer than
this will be rejected. Defaults to 3000.

.. setting:: COMMENTS_APP

COMMENTS_APP
------------

An app which provides :doc:`customization of the comments framework
</ref/contrib/comments/custom>`.  Use the same dotted-string notation
as in :setting:`INSTALLED_APPS`.  Your custom :setting:`COMMENTS_APP`
must also be listed in :setting:`INSTALLED_APPS`.
