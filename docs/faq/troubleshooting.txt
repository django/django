===============
Troubleshooting
===============

This page contains some advice about errors and problems commonly encountered
during the development of Django applications.

.. _troubleshooting-django-admin-py:

Problems running django-admin.py
================================

"command not found: django-admin.py"
------------------------------------

:doc:`django-admin.py </ref/django-admin>` should be on your system path if you
installed Django via ``python setup.py``. If it's not on your path, you can
find it in ``site-packages/django/bin``, where ``site-packages`` is a directory
within your Python installation. Consider symlinking to :doc:`django-admin.py
</ref/django-admin>` from some place on your path, such as
:file:`/usr/local/bin`.

Script name may differ in distribution packages
-----------------------------------------------

If you installed Django using a Linux distribution's package manager
(e.g. ``apt-get`` or ``yum``) ``django-admin.py`` may have been renamed to
``django-admin``; use that instead.

Mac OS X permissions
--------------------

If you're using Mac OS X, you may see the message "permission denied" when
you try to run ``django-admin.py``. This is because, on Unix-based systems like
OS X, a file must be marked as "executable" before it can be run as a program.
To do this, open Terminal.app and navigate (using the ``cd`` command) to the
directory where :doc:`django-admin.py </ref/django-admin>` is installed, then
run the command ``sudo chmod +x django-admin.py``.

Running virtualenv on Windows
-----------------------------

If you used virtualenv_ to :ref:`install Django <installing-official-release>`
on Windows, you may get an ``ImportError`` when you try to run
``django-admin.py``. This is because Windows does not run the
Python interpreter from your virtual environment unless you invoke it
directly. Instead, prefix all commands that use .py files with ``python`` and
use the full path to the file, like so:
``python C:\pythonXY\Scripts\django-admin.py``.

.. _virtualenv: http://www.virtualenv.org/
