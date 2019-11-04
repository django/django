==========================
Django 1.9.8 release notes
==========================

*July 18, 2016*

Django 1.9.8 fixes a security issue and several bugs in 1.9.7.

XSS in admin's add/change related popup
=======================================

Unsafe usage of JavaScript's ``Element.innerHTML`` could result in XSS in the
admin's add/change related popup. ``Element.textContent`` is now used to
prevent execution of the data.

The debug view also used ``innerHTML``. Although a security issue wasn't
identified there, out of an abundance of caution it's also updated to use
``textContent``.

Bugfixes
========

* Fixed missing ``varchar/text_pattern_ops`` index on ``CharField`` and
  ``TextField`` respectively when using ``AddField`` on PostgreSQL
  (:ticket:`26889`).

* Fixed ``makemessages`` crash on Python 2 with non-ASCII file names
  (:ticket:`26897`).
