=============
API stability
=============

Django promises API stability and forwards-compatibility since version 1.0. In
a nutshell, this means that code you develop against a version of Django will
continue to work with future releases. You may need to make minor changes when
upgrading the version of Django your project uses: see the "Backwards
incompatible changes" section of the :doc:`release note </releases/index>` for
the version or versions to which you are upgrading.

What "stable" means
===================

In this context, stable means:

- All the public APIs (everything in this documentation) will not be moved
  or renamed without providing backwards-compatible aliases.

- If new features are added to these APIs -- which is quite possible --
  they will not break or change the meaning of existing methods. In other
  words, "stable" does not (necessarily) mean "complete."

- If, for some reason, an API declared stable must be removed or replaced, it
  will be declared deprecated but will remain in the API for at least two
  feature releases. Warnings will be issued when the deprecated method is
  called.

  See :ref:`official-releases` for more details on how Django's version
  numbering scheme works, and how features will be deprecated.

- We'll only break backwards compatibility of these APIs if a bug or
  security hole makes it completely unavoidable.

Stable APIs
===========

In general, everything covered in the documentation -- with the exception of
anything in the :doc:`internals area </internals/index>` is considered stable.

Exceptions
==========

There are a few exceptions to this stability and backwards-compatibility
promise.

Security fixes
--------------

If we become aware of a security problem -- hopefully by someone following our
:ref:`security reporting policy <reporting-security-issues>` -- we'll do
everything necessary to fix it. This might mean breaking backwards
compatibility; security trumps the compatibility guarantee.

APIs marked as internal
-----------------------

Certain APIs are explicitly marked as "internal" in a couple of ways:

- Some documentation refers to internals and mentions them as such. If the
  documentation says that something is internal, we reserve the right to
  change it.

- Functions, methods, and other objects prefixed by a leading underscore
  (``_``). This is the standard Python way of indicating that something is
  private; if any method starts with a single ``_``, it's an internal API.
