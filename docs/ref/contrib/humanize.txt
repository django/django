========================
django.contrib.humanize
========================

.. module:: django.contrib.humanize
   :synopsis: A set of Django template filters useful for adding a "human
              touch" to data.

A set of Django template filters useful for adding a "human touch" to data.

To activate these filters, add ``'django.contrib.humanize'`` to your
:setting:`INSTALLED_APPS` setting. Once you've done that, use
``{% load humanize %}`` in a template, and you'll have access to the following
filters.

.. templatefilter:: apnumber

apnumber
--------

For numbers 1-9, returns the number spelled out. Otherwise, returns the
number. This follows Associated Press style.

Examples:

* ``1`` becomes ``one``.
* ``2`` becomes ``two``.
* ``10`` becomes ``10``.

You can pass in either an integer or a string representation of an integer.

.. templatefilter:: intcomma

intcomma
--------

Converts an integer to a string containing commas every three digits.

Examples:

* ``4500`` becomes ``4,500``.
* ``45000`` becomes ``45,000``.
* ``450000`` becomes ``450,000``.
* ``4500000`` becomes ``4,500,000``.

:ref:`Format localization <format-localization>` will be respected if enabled,
e.g. with the ``'de'`` language:

* ``45000`` becomes ``'45.000'``.
* ``450000`` becomes ``'450.000'``.

You can pass in either an integer or a string representation of an integer.

.. templatefilter:: intword

intword
-------

Converts a large integer to a friendly text representation. Works best for
numbers over 1 million.

Examples:

* ``1000000`` becomes ``1.0 million``.
* ``1200000`` becomes ``1.2 million``.
* ``1200000000`` becomes ``1.2 billion``.

Values up to 10^100 (Googol) are supported.

:ref:`Format localization <format-localization>` will be respected if enabled,
e.g. with the ``'de'`` language:

* ``1000000`` becomes ``'1,0 Million'``.
* ``1200000`` becomes ``'1,2 Million'``.
* ``1200000000`` becomes ``'1,2 Milliarden'``.

You can pass in either an integer or a string representation of an integer.

.. templatefilter:: naturalday

naturalday
----------

For dates that are the current day or within one day, return "today",
"tomorrow" or "yesterday", as appropriate. Otherwise, format the date using
the passed in format string.

**Argument:** Date formatting string as described in the :tfilter:`date` tag.

Examples (when 'today' is 17 Feb 2007):

* ``16 Feb 2007`` becomes ``yesterday``.
* ``17 Feb 2007`` becomes ``today``.
* ``18 Feb 2007`` becomes ``tomorrow``.
* Any other day is formatted according to given argument or the
  :setting:`DATE_FORMAT` setting if no argument is given.

.. templatefilter:: naturaltime

naturaltime
-----------

For datetime values, returns a string representing how many seconds,
minutes or hours ago it was -- falling back to the :tfilter:`timesince`
format if the value is more than a day old. In case the datetime value is in
the future the return value will automatically use an appropriate phrase.

Examples (when 'now' is 17 Feb 2007 16:30:00):

* ``17 Feb 2007 16:30:00`` becomes ``now``.
* ``17 Feb 2007 16:29:31`` becomes ``29 seconds ago``.
* ``17 Feb 2007 16:29:00`` becomes ``a minute ago``.
* ``17 Feb 2007 16:25:35`` becomes ``4 minutes ago``.
* ``17 Feb 2007 15:30:29`` becomes ``an hour ago``.
* ``17 Feb 2007 13:31:29`` becomes ``2 hours ago``.
* ``16 Feb 2007 13:31:29`` becomes ``1 day, 3 hours ago``.
* ``17 Feb 2007 16:30:30`` becomes ``29 seconds from now``.
* ``17 Feb 2007 16:31:00`` becomes ``a minute from now``.
* ``17 Feb 2007 16:34:35`` becomes ``4 minutes from now``.
* ``17 Feb 2007 16:30:29`` becomes ``an hour from now``.
* ``17 Feb 2007 18:31:29`` becomes ``2 hours from now``.
* ``18 Feb 2007 16:31:29`` becomes ``1 day from now``.
* ``26 Feb 2007 18:31:29`` becomes ``1 week, 2 days from now``.

.. templatefilter:: ordinal

ordinal
-------

Converts an integer to its ordinal as a string.

Examples:

* ``1`` becomes ``1st``.
* ``2`` becomes ``2nd``.
* ``3`` becomes ``3rd``.

You can pass in either an integer or a string representation of an integer.
