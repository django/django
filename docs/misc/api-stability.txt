=============
API stability
=============

Django is committed to API stability and forwards-compatibility. In a nutshell,
this means that code you develop against a version of Django will continue to
work with future releases. You may need to make minor changes when upgrading
the version of Django your project uses: see the "Backwards incompatible
changes" section of the :doc:`release note </releases/index>` for the version
or versions to which you are upgrading.

At the same time as making API stability a very high priority, Django is also
committed to continual improvement, along with aiming for "one way to do it"
(eventually) in the APIs we provide. This means that when we discover clearly
superior ways to do things, we will deprecate and eventually remove the old
ways. Our aim is to provide a modern, dependable web framework of the highest
quality that encourages best practices in all projects that use it. By using
incremental improvements, we try to avoid both stagnation and large breaking
upgrades.

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

- We'll only break backwards compatibility of these APIs without a deprecation
  process if a bug or security hole makes it completely unavoidable.

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
