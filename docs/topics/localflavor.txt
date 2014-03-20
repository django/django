==========================
The "local flavor" add-ons
==========================

Historically, Django has shipped with ``django.contrib.localflavor`` --
assorted pieces of code that are useful for particular countries or cultures.
This code is now distributed separately from Django, for easier maintenance
and to trim the size of Django's codebase.

The new localflavor package is named ``django-localflavor``, with a main
module called ``localflavor`` and many subpackages using an
`ISO 3166 country code`_. For example: ``localflavor.us`` is the
localflavor package for the U.S.A.

Most of these ``localflavor`` add-ons are country-specific fields for the
:doc:`forms </topics/forms/index>` framework -- for example, a
``USStateField`` that knows how to validate U.S. state abbreviations and a
``FISocialSecurityNumber`` that knows how to validate Finnish social security
numbers.

To use one of these localized components, just import the relevant subpackage.
For example, here's how you can create a form with a field representing a
French telephone number::

    from django import forms
    from localflavor.fr.forms import FRPhoneNumberField

    class MyForm(forms.Form):
        my_french_phone_no = FRPhoneNumberField()

For documentation on a given country's localflavor helpers, see its README
file.

.. _ISO 3166 country code: http://www.iso.org/iso/country_codes.htm

.. _localflavor-packages:

Supported countries
===================

See the official documentation for more information:

    https://django-localflavor.readthedocs.org/

Internationalization of localflavors
====================================

To activate translations for the ``localflavor`` application, you must include
the application's name in the :setting:`INSTALLED_APPS` setting, so the
internationalization system can find the catalog, as explained in
:ref:`how-django-discovers-translations`.

.. _localflavor-how-to-migrate:

How to migrate
==============

If you've used the old ``django.contrib.localflavor`` package or one of the
temporary ``django-localflavor-*`` releases, follow these two easy steps to
update your code:

1. Install the third-party ``django-localflavor`` package from PyPI.

2. Change your app's import statements to reference the new package.

   For example, change this::

       from django.contrib.localflavor.fr.forms import FRPhoneNumberField

   ...to this::

       from localflavor.fr.forms import FRPhoneNumberField

The code in the new package is the same (it was copied directly from Django),
so you don't have to worry about backwards compatibility in terms of
functionality. Only the imports have changed.

.. _localflavor-deprecation-policy:

Deprecation policy
==================

In Django 1.5, importing from ``django.contrib.localflavor`` will result in a
``DeprecationWarning``. This means your code will still work, but you should
change it as soon as possible.

In Django 1.6, importing from ``django.contrib.localflavor`` will no longer
work.
