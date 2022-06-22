===========================
Django 3.2.14 release notes
===========================

*July 4, 2022*

Django 3.2.14 fixes a security issue with severity "high" in 3.2.13.

CVE-2022-34265: Potential SQL injection via ``Trunc(kind)`` and ``Extract(lookup_name)`` arguments
==================================================================================================

:class:`Trunc() <django.db.models.functions.Trunc>` and
:class:`Extract() <django.db.models.functions.Extract>` database functions were
subject to SQL injection if untrusted data was used as a
``kind``/``lookup_name`` value.

Applications that constrain the lookup name and kind choice to a known safe
list are unaffected.
