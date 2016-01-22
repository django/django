=================
Localizing Django
=================

Various parts of Django, such as the admin site and validation error messages,
are internationalized. This means they display differently depending on each
user's language or country. For this, Django uses the same internationalization
and localization infrastructure available to Django applications, described in
the :doc:`i18n documentation </topics/i18n/index>`.

Translations
============

Translations are contributed by Django users worldwide. The translation work is
coordinated at `Transifex`_.

If you find an incorrect translation or want to discuss specific translations,
go to the `Django project page`_. If you would like to help out with
translating or add a language that isn't yet translated, here's what to do:

* Join the :ref:`Django i18n mailing list <django-i18n-mailing-list>` and
  introduce yourself.

* Make sure you read the notes about :ref:`specialties-of-django-i18n`.

* Sign up at `Transifex`_ and visit the `Django project page`_.

* On the `Django project page`_, choose the language you want to work on,
  **or** -- in case the language doesn't exist yet --
  request a new language team by clicking on the "Request language" link
  and selecting the appropriate language.

* Then, click the "Join this Team" button to become a member of this team.
  Every team has at least one coordinator who is responsible to review
  your membership request. You can of course also contact the team
  coordinator to clarify procedural problems and handle the actual
  translation process.

* Once you are a member of a team choose the translation resource you
  want to update on the team page. For example the "core" resource refers
  to the translation catalog that contains all non-contrib translations.
  Each of the contrib apps also have a resource (prefixed with "contrib").

  .. note::
     For more information about how to use Transifex, read the
     `Transifex User Guide`_.

Translations from Transifex are only integrated into the Django repository at
the time of a new :term:`feature release`. We try to update them a second time
during one of the following :term:`patch release`\s, but that depends on the
translation manager's availability. So don't miss the string freeze period
(between the release candidate and the feature release) to take the opportunity
to complete and fix the translations for your language!

Formats
=======

You can also review ``conf/locale/<locale>/formats.py``. This file describes
the date, time and numbers formatting particularities of your locale. See
:doc:`/topics/i18n/formatting` for details.

The format files aren't managed by the use of Transifex. To change them, you
must :doc:`create a patch<writing-code/submitting-patches>` against the
Django source tree, as for any code change:

* Create a diff against the current Git master branch.

* Open a ticket in Django's ticket system, set its ``Component`` field to
  ``Translations``, and attach the patch to it.

.. _Transifex: https://www.transifex.com/
.. _Django project page: https://www.transifex.com/django/django/
.. _Transifex User Guide: http://docs.transifex.com/

.. _translating-documentation:

Documentation
=============

There is also an opportunity to translate the documentation, though this is a
huge undertaking to complete entirely (you have been warned!). We use the same
`Transifex tool <https://www.transifex.com/django/django-docs/>`_. The
translations will appear at ``https://docs.djangoproject.com/<language_code>/``
when at least the ``docs/intro/*`` files are fully translated in your language.
