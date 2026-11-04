===================
Quick install guide
===================

Before you can use Django, you'll need to get it installed. We have a
:doc:`complete installation guide </topics/install>` that covers all the
possibilities; this guide will guide you to a minimal installation that'll work
while you walk through the introduction.

Install Python
==============

Being a Python web framework, Django requires Python. See
:ref:`faq-python-version-support` for details. Python includes a lightweight
database called SQLite_ so you won't need to set up a database just yet.

.. _sqlite: https://www.sqlite.org/

Get the latest version of Python at https://www.python.org/downloads/ or with
your operating system's package manager.

You can verify that Python is installed by typing ``python`` from your shell;
you should see something like:

.. code-block:: pycon

    Python 3.x.y
    [GCC 4.x] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>>

Set up a database
=================

This step is only necessary if you'd like to work with a "large" database
engine like PostgreSQL, MariaDB, MySQL, or Oracle. To install such a database,
consult the :ref:`database installation information <database-installation>`.

Install Django
==============

You've got three options to install Django:

* :ref:`Install an official release <installing-official-release>`. This
  is the best approach for most users.

* Install a version of Django :ref:`provided by your operating system
  distribution <installing-distribution-package>`.

* :ref:`Install the latest development version
  <installing-development-version>`. This option is for enthusiasts who want
  the latest-and-greatest features and aren't afraid of running brand new code.
  You might encounter new bugs in the development version, but reporting them
  helps the development of Django. Also, releases of third-party packages are
  less likely to be compatible with the development version than with the
  latest stable release.

.. admonition:: Always refer to the documentation that corresponds to the
    version of Django you're using!

    The main documentation site at `docs.djangoproject.com`_ shows the latest
    stable release by default. If you've installed a different Django version,
    be sure to switch to the correct documentation using the version picker at
    the bottom. Keep an eye out for "added/changed/deprecated in version ..."
    notes which flag features that may be different from the version you're
    using.

.. _docs.djangoproject.com: https://docs.djangoproject.com/

Verifying
=========

To verify that Django can be seen by Python, type ``python`` from your shell.
Then at the Python prompt, try to import Django:

.. parsed-literal::

    >>> import django
    >>> print(django.get_version())
    |version|

You may have another version of Django installed.

That's it!
==========

That's it -- you can now :doc:`move onto the tutorial </intro/tutorial01>`.
