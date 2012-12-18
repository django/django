=====================
How to install Django
=====================

This document will get you up and running with Django.

Install Python
==============

Being a Python Web framework, Django requires Python.

It works with any Python version from 2.6.5 to 2.7. It also features
experimental support for versions from 3.2.3 to 3.3.

Get Python at http://www.python.org. If you're running Linux or Mac OS X, you
probably already have it installed.

.. admonition:: Django on Jython

    If you use Jython_ (a Python implementation for the Java platform), you'll
    need to follow a few additional steps. See :doc:`/howto/jython` for details.

.. _jython: http://jython.org/

.. admonition:: Python on Windows

    On Windows, you might need to adjust your ``PATH`` environment variable
    to include paths to Python executable and additional scripts. For example,
    if your Python is installed in ``C:\Python27\``, the following paths need
    to be added to ``PATH``::

        C:\Python27\;C:\Python27\Scripts;

Install Apache and mod_wsgi
=============================

If you just want to experiment with Django, skip ahead to the next
section; Django includes a lightweight web server you can use for
testing, so you won't need to set up Apache until you're ready to
deploy Django in production.

If you want to use Django on a production site, use `Apache`_ with
`mod_wsgi`_. mod_wsgi can operate in one of two modes: an embedded
mode and a daemon mode. In embedded mode, mod_wsgi is similar to
mod_perl -- it embeds Python within Apache and loads Python code into
memory when the server starts. Code stays in memory throughout the
life of an Apache process, which leads to significant performance
gains over other server arrangements. In daemon mode, mod_wsgi spawns
an independent daemon process that handles requests. The daemon
process can run as a different user than the Web server, possibly
leading to improved security, and the daemon process can be restarted
without restarting the entire Apache Web server, possibly making
refreshing your codebase more seamless. Consult the mod_wsgi
documentation to determine which mode is right for your setup. Make
sure you have Apache installed, with the mod_wsgi module activated.
Django will work with any version of Apache that supports mod_wsgi.

See :doc:`How to use Django with mod_wsgi </howto/deployment/wsgi/modwsgi>`
for information on how to configure mod_wsgi once you have it
installed.

If you can't use mod_wsgi for some reason, fear not: Django supports many other
deployment options. One is :doc:`uWSGI </howto/deployment/wsgi/uwsgi>`; it works
very well with `nginx`_. Another is :doc:`FastCGI </howto/deployment/fastcgi>`,
perfect for using Django with servers other than Apache. Additionally, Django
follows the WSGI spec (:pep:`3333`), which allows it to run on a variety of
server platforms. See the `server-arrangements wiki page`_ for specific
installation instructions for each platform.

.. _Apache: http://httpd.apache.org/
.. _nginx: http://nginx.org/
.. _mod_wsgi: http://code.google.com/p/modwsgi/
.. _server-arrangements wiki page: https://code.djangoproject.com/wiki/ServerArrangements

.. _database-installation:

Get your database running
=========================

If you plan to use Django's database API functionality, you'll need to make
sure a database server is running. Django supports many different database
servers and is officially supported with PostgreSQL_, MySQL_, Oracle_ and
SQLite_.

If you are developing a simple project or something you don't plan to deploy
in a production environment, SQLite is generally the simplest option as it
doesn't require running a separate server. However, SQLite has many differences
from other databases, so if you are working on something substantial, it's
recommended to develop with the same database as you plan on using in
production.

In addition to the officially supported databases, there are backends provided
by 3rd parties that allow you to use other databases with Django:

* `Sybase SQL Anywhere`_
* `IBM DB2`_
* `Microsoft SQL Server 2005`_
* Firebird_
* ODBC_

The Django versions and ORM features supported by these unofficial backends
vary considerably. Queries regarding the specific capabilities of these
unofficial backends, along with any support queries, should be directed to the
support channels provided by each 3rd party project.

In addition to a database backend, you'll need to make sure your Python
database bindings are installed.

* If you're using PostgreSQL, you'll need the `postgresql_psycopg2`_ package.
  You might want to refer to our :ref:`PostgreSQL notes <postgresql-notes>` for
  further technical details specific to this database.

  If you're on Windows, check out the unofficial `compiled Windows version`_.

* If you're using MySQL, you'll need the ``MySQL-python`` package, version
  1.2.1p2 or higher. You will also want to read the database-specific
  :ref:`notes for the MySQL backend <mysql-notes>`.

* If you're using Oracle, you'll need a copy of cx_Oracle_, but please
  read the database-specific :ref:`notes for the Oracle backend <oracle-notes>`
  for important information regarding supported versions of both Oracle and
  ``cx_Oracle``.

* If you're using an unofficial 3rd party backend, please consult the
  documentation provided for any additional requirements.

If you plan to use Django's ``manage.py syncdb`` command to automatically
create database tables for your models (after first installing Django and
creating a project), you'll need to ensure that Django has permission to create
and alter tables in the database you're using; if you plan to manually create
the tables, you can simply grant Django ``SELECT``, ``INSERT``, ``UPDATE`` and
``DELETE`` permissions. On some databases, Django will need ``ALTER TABLE``
privileges during ``syncdb`` but won't issue ``ALTER TABLE`` statements on a
table once ``syncdb`` has created it. After creating a database user with these
permissions, you'll specify the details in your project's settings file,
see :setting:`DATABASES` for details.

If you're using Django's :doc:`testing framework</topics/testing/index>` to test
database queries, Django will need permission to create a test database.

.. _PostgreSQL: http://www.postgresql.org/
.. _MySQL: http://www.mysql.com/
.. _postgresql_psycopg2: http://initd.org/psycopg/
.. _compiled Windows version: http://stickpeople.com/projects/python/win-psycopg/
.. _SQLite: http://www.sqlite.org/
.. _pysqlite: http://trac.edgewall.org/wiki/PySqlite
.. _cx_Oracle: http://cx-oracle.sourceforge.net/
.. _Oracle: http://www.oracle.com/
.. _Sybase SQL Anywhere: http://code.google.com/p/sqlany-django/
.. _IBM DB2: http://code.google.com/p/ibm-db/
.. _Microsoft SQL Server 2005: http://code.google.com/p/django-mssql/
.. _Firebird: http://code.google.com/p/django-firebird/
.. _ODBC: http://code.google.com/p/django-pyodbc/
.. _removing-old-versions-of-django:

Remove any old versions of Django
=================================

If you are upgrading your installation of Django from a previous version,
you will need to uninstall the old Django version before installing the
new version.

If you installed Django using pip_ or ``easy_install`` previously, installing
with pip_ or ``easy_install`` again will automatically take care of the old
version, so you don't need to do it yourself.

If you previously installed Django using ``python setup.py install``,
uninstalling is as simple as deleting the ``django`` directory from your Python
``site-packages``. To find the directory you need to remove, you can run the
following at your shell prompt (not the interactive Python prompt):

.. code-block:: bash

    python -c "import sys; sys.path = sys.path[1:]; import django; print(django.__path__)"


.. _install-django-code:

Install the Django code
=======================

Installation instructions are slightly different depending on whether you're
installing a distribution-specific package, downloading the latest official
release, or fetching the latest development version.

It's easy, no matter which way you choose.

Installing a distribution-specific package
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Check the :doc:`distribution specific notes </misc/distributions>` to see if
your platform/distribution provides official Django packages/installers.
Distribution-provided packages will typically allow for automatic installation
of dependencies and easy upgrade paths.

.. _installing-official-release:

Installing an official release with ``pip``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the recommended way to install Django.

1. Install pip_. The easiest is to use the `standalone pip installer`_. If your
   distribution already has ``pip`` installed, you might need to update it if
   it's outdated. (If it's outdated, you'll know because installation won't
   work.)

2. (optional) Take a look at virtualenv_ and virtualenvwrapper_. These tools
   provide isolated Python environments, which are more practical than
   installing packages systemwide. They also allow installing packages
   without administrator privileges. It's up to you to decide if you want to
   learn and use them.

3. If you're using Linux, Mac OS X or some other flavor of Unix, enter the
   command ``sudo pip install Django`` at the shell prompt. If you're using
   Windows, start a command shell with administrator privileges and run
   the command ``pip install Django``. This will install Django in your Python
   installation's ``site-packages`` directory.

   If you're using a virtualenv, you don't need ``sudo`` or administrator
   privileges, and this will install Django in the virtualenv's
   ``site-packages`` directory.

.. _pip: http://www.pip-installer.org/
.. _virtualenv: http://www.virtualenv.org/
.. _virtualenvwrapper: http://www.doughellmann.com/docs/virtualenvwrapper/
.. _standalone pip installer: http://www.pip-installer.org/en/latest/installing.html#using-the-installer

Installing an official release manually
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Download the latest release from our `download page`_.

2. Untar the downloaded file (e.g. ``tar xzvf Django-X.Y.tar.gz``,
   where ``X.Y`` is the version number of the latest release).
   If you're using Windows, you can download the command-line tool
   bsdtar_ to do this, or you can use a GUI-based tool such as 7-zip_.

3. Change into the directory created in step 2 (e.g. ``cd Django-X.Y``).

4. If you're using Linux, Mac OS X or some other flavor of Unix, enter the
   command ``sudo python setup.py install`` at the shell prompt. If you're
   using Windows, start a command shell with administrator privileges and
   run the command ``python setup.py install``. This will install Django in
   your Python installation's ``site-packages`` directory.

   .. admonition:: Removing an old version

       If you use this installation technique, it is particularly important
       that you :ref:`remove any existing
       installations<removing-old-versions-of-django>` of Django
       first. Otherwise, you can end up with a broken installation that
       includes files from previous versions that have since been removed from
       Django.

.. _download page: https://www.djangoproject.com/download/
.. _bsdtar: http://gnuwin32.sourceforge.net/packages/bsdtar.htm
.. _7-zip: http://www.7-zip.org/

.. _installing-development-version:

Installing the development version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. admonition:: Tracking Django development

    If you decide to use the latest development version of Django,
    you'll want to pay close attention to `the development timeline`_,
    and you'll want to keep an eye on the :ref:`release notes for the
    upcoming release <development_release_notes>`. This will help you stay
    on top of any new features you might want to use, as well as any changes
    you'll need to make to your code when updating your copy of Django.
    (For stable releases, any necessary changes are documented in the
    release notes.)

.. _the development timeline: https://code.djangoproject.com/timeline

If you'd like to be able to update your Django code occasionally with the
latest bug fixes and improvements, follow these instructions:

1. Make sure that you have Git_ installed and that you can run its commands
   from a shell. (Enter ``git help`` at a shell prompt to test this.)

2. Check out Django's main development branch (the 'trunk' or 'master') like
   so:

   .. code-block:: bash

       git clone git://github.com/django/django.git django-trunk

   This will create a directory ``django-trunk`` in your current directory.

3. Make sure that the Python interpreter can load Django's code. The most
   convenient way to do this is via pip_. Run the following command:

   .. code-block:: bash

       sudo pip install -e django-trunk/

   (If using a virtualenv_ you can omit ``sudo``.)

   This will make Django's code importable, and will also make the
   ``django-admin.py`` utility command available. In other words, you're all
   set!

   If you don't have pip_ available, see the alternative instructions for
   `installing the development version without pip`_.

.. warning::

    Don't run ``sudo python setup.py install``, because you've already
    carried out the equivalent actions in step 3.

When you want to update your copy of the Django source code, just run the
command ``git pull`` from within the ``django-trunk`` directory. When you do
this, Git will automatically download any changes.

.. _Git: http://git-scm.com/
.. _`modify Python's search path`: http://docs.python.org/install/index.html#modifying-python-s-search-path
.. _installing-the-development-version-without-pip:

Installing the development version without pip
----------------------------------------------

If you don't have pip_, you can instead manually `modify Python's search
path`_.

First follow steps 1 and 2 above, so that you have a ``django-trunk`` directory
with a checkout of Django's latest code in it. Then add a ``.pth`` file
containing the full path to the ``django-trunk`` directory to your system's
``site-packages`` directory. For example, on a Unix-like system:

.. code-block:: bash

    echo WORKING-DIR/django-trunk > SITE-PACKAGES-DIR/django.pth

In the above line, change ``WORKING-DIR/django-trunk`` to match the full path
to your new ``django-trunk`` directory, and change ``SITE-PACKAGES-DIR`` to
match the location of your system's ``site-packages`` directory.

The location of the ``site-packages`` directory depends on the operating
system, and the location in which Python was installed. To find your system's
``site-packages`` location, execute the following:

.. code-block:: bash

    python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())"

(Note that this should be run from a shell prompt, not a Python interactive
prompt.)

Some Debian-based Linux distributions have separate ``site-packages``
directories for user-installed packages, such as when installing Django from
a downloaded tarball. The command listed above will give you the system's
``site-packages``, the user's directory can be found in ``/usr/local/lib/``
instead of ``/usr/lib/``.

Next you need to make the ``django-admin.py`` utility available in your
shell PATH.

On Unix-like systems, create a symbolic link to the file
``django-trunk/django/bin/django-admin.py`` in a directory on your system
path, such as ``/usr/local/bin``. For example:

.. code-block:: bash

    ln -s WORKING-DIR/django-trunk/django/bin/django-admin.py /usr/local/bin/

(In the above line, change WORKING-DIR to match the full path to your new
``django-trunk`` directory.)

This simply lets you type ``django-admin.py`` from within any directory,
rather than having to qualify the command with the full path to the file.

On Windows systems, the same result can be achieved by copying the file
``django-trunk/django/bin/django-admin.py`` to somewhere on your system
path, for example ``C:\Python27\Scripts``.
