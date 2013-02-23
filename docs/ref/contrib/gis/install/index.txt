.. _ref-gis-install:

======================
GeoDjango Installation
======================

.. highlight:: console

Overview
========
In general, GeoDjango installation requires:

1. :ref:`Python and Django <django>`
2. :ref:`spatial_database`
3. :ref:`geospatial_libs`

Details for each of the requirements and installation instructions
are provided in the sections below. In addition, platform-specific
instructions are available for:

* :ref:`macosx`
* :ref:`windows`

.. admonition:: Use the Source

    Because GeoDjango takes advantage of the latest in the open source geospatial
    software technology, recent versions of the libraries are necessary.
    If binary packages aren't available for your platform, installation from
    source may be required. When compiling the libraries from source, please
    follow the directions closely, especially if you're a beginner.

Requirements
============

.. _django:

Python and Django
-----------------

Because GeoDjango is included with Django, please refer to Django's
:ref:`installation instructions <installing-official-release>` for details on
how to install.


.. _spatial_database:

Spatial database
----------------
PostgreSQL (with PostGIS), MySQL (mostly with MyISAM engine), Oracle, and SQLite
(with SpatiaLite) are the spatial databases currently supported.

.. note::

    PostGIS is recommended, because it is the most mature and feature-rich
    open source spatial database.

The geospatial libraries required for a GeoDjango installation depends
on the spatial database used.  The following lists the library requirements,
supported versions, and any notes for each of the supported database backends:

==================  ==============================  ==================  =========================================
Database            Library Requirements            Supported Versions  Notes
==================  ==============================  ==================  =========================================
PostgreSQL          GEOS, PROJ.4, PostGIS           8.2+                Requires PostGIS.
MySQL               GEOS                            5.x                 Not OGC-compliant; :ref:`limited functionality <mysql-spatial-limitations>`.
Oracle              GEOS                            10.2, 11            XE not supported; not tested with 9.
SQLite              GEOS, GDAL, PROJ.4, SpatiaLite  3.6.+               Requires SpatiaLite 2.3+, pysqlite2 2.5+
==================  ==============================  ==================  =========================================

See also `this comparison matrix`__ on the OSGeo Wiki for
PostgreSQL/PostGIS/GEOS/GDAL possible combinations.

__ http://trac.osgeo.org/postgis/wiki/UsersWikiPostgreSQLPostGIS

Installation
============

Geospatial libraries
--------------------

.. toctree::
   :maxdepth: 1

   geolibs

Database installation
---------------------

.. toctree::
   :maxdepth: 1

   postgis
   spatialite

Add ``django.contrib.gis`` to :setting:`INSTALLED_APPS`
-------------------------------------------------------

Like other Django contrib applications, you will *only* need to add
:mod:`django.contrib.gis` to :setting:`INSTALLED_APPS` in your settings.
This is the so that ``gis`` templates can be located -- if not done, then
features such as the geographic admin or KML sitemaps will not function properly.

.. _addgoogleprojection:

Add Google projection to ``spatial_ref_sys`` table
--------------------------------------------------

.. note::

    If you're running PostGIS 1.4 or above, you can skip this step. The entry
    is already included in the default ``spatial_ref_sys`` table.

In order to conduct database transformations to the so-called "Google"
projection (a spherical mercator projection used by Google Maps),
an entry must be added to your spatial database's ``spatial_ref_sys`` table.
Invoke the Django shell from your project and execute the
``add_srs_entry`` function:

.. code-block:: pycon

    $ python manage.py shell
    >>> from django.contrib.gis.utils import add_srs_entry
    >>> add_srs_entry(900913)

This adds an entry for the 900913 SRID to the ``spatial_ref_sys`` (or equivalent)
table, making it possible for the spatial database to transform coordinates in
this projection.  You only need to execute this command *once* per spatial database.

Troubleshooting
===============

If you can't find the solution to your problem here then participate in the
community!  You can:

* Join the ``#geodjango`` IRC channel on FreeNode. Please be patient and polite
  -- while you may not get an immediate response, someone will attempt to answer
  your question as soon as they see it.
* Ask your question on the `GeoDjango`__ mailing list.
* File a ticket on the `Django trac`__ if you think there's a bug.  Make
  sure to provide a complete description of the problem, versions used,
  and specify the component as "GIS".

__ http://groups.google.com/group/geodjango
__ https://code.djangoproject.com/newticket

.. _libsettings:

Library environment settings
----------------------------

By far, the most common problem when installing GeoDjango is that the
external shared libraries (e.g., for GEOS and GDAL) cannot be located. [#]_
Typically, the cause of this problem is that the operating system isn't aware
of the directory where the libraries built from source were installed.

In general, the library path may be set on a per-user basis by setting
an environment variable, or by configuring the library path for the entire
system.

``LD_LIBRARY_PATH`` environment variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A user may set this environment variable to customize the library paths
they want to use.  The typical library directory for software
built from source is ``/usr/local/lib``.  Thus, ``/usr/local/lib`` needs
to be included in the ``LD_LIBRARY_PATH`` variable.  For example, the user
could place the following in their bash profile::

    export LD_LIBRARY_PATH=/usr/local/lib

Setting system library path
^^^^^^^^^^^^^^^^^^^^^^^^^^^

On GNU/Linux systems, there is typically a file in ``/etc/ld.so.conf``, which may include
additional paths from files in another directory, such as ``/etc/ld.so.conf.d``.
As the root user, add the custom library path (like ``/usr/local/lib``) on a
new line in ``ld.so.conf``.  This is *one* example of how to do so::

    $ sudo echo /usr/local/lib >> /etc/ld.so.conf
    $ sudo ldconfig

For OpenSolaris users, the system library path may be modified using the
``crle`` utility.  Run ``crle`` with no options to see the current configuration
and use ``crle -l`` to set with the new library path.  Be *very* careful when
modifying the system library path::

    # crle -l $OLD_PATH:/usr/local/lib

.. _binutils:

Install ``binutils``
^^^^^^^^^^^^^^^^^^^^

GeoDjango uses the ``find_library`` function (from the ``ctypes.util`` Python
module) to discover libraries.  The ``find_library`` routine uses a program
called ``objdump`` (part of the ``binutils`` package) to verify a shared
library on GNU/Linux systems.  Thus, if ``binutils`` is not installed on your
Linux system then Python's ctypes may not be able to find your library even if
your library path is set correctly and geospatial libraries were built perfectly.

The ``binutils`` package may be installed on Debian and Ubuntu systems using the
following command::

    $ sudo apt-get install binutils

Similarly, on Red Hat and CentOS systems::

    $ sudo yum install binutils

Platform-specific instructions
==============================

.. _macosx:

Mac OS X
--------

Because of the variety of packaging systems available for OS X, users have
several different options for installing GeoDjango. These options are:

* :ref:`homebrew`
* :ref:`kyngchaos`
* :ref:`fink`
* :ref:`macports`
* :ref:`build_from_source`

.. note::

    Currently, the easiest and recommended approach for installing GeoDjango
    on OS X is to use the KyngChaos packages.

This section also includes instructions for installing an upgraded version
of :ref:`macosx_python` from packages provided by the Python Software
Foundation, however, this is not required.

.. _macosx_python:

Python
^^^^^^

Although OS X comes with Python installed, users can use framework
installers (`2.6`__ and `2.7`__ are available) provided by
the Python Software Foundation.  An advantage to using the installer is
that OS X's Python will remain "pristine" for internal operating system
use.

__ http://python.org/ftp/python/2.6.6/python-2.6.6-macosx10.3.dmg
__ http://python.org/ftp/python/2.7.3/

.. note::

    You will need to modify the ``PATH`` environment variable in your
    ``.profile`` file so that the new version of Python is used when
    ``python`` is entered at the command-line::

        export PATH=/Library/Frameworks/Python.framework/Versions/Current/bin:$PATH

.. _homebrew:

Homebrew
^^^^^^^^

`Homebrew`__ provides "recipes" for building binaries and packages from source.
It provides recipes for the GeoDjango prerequisites on Macintosh computers
running OS X. Because Homebrew still builds the software from source, the
`Apple Developer Tools`_ are required.

Summary::

    $ brew install postgresql
    $ brew install postgis
    $ brew install gdal
    $ brew install libgeoip

__ http://mxcl.github.com/homebrew/
.. _Apple Developer Tools: https://developer.apple.com/technologies/tools/

.. _kyngchaos:

KyngChaos packages
^^^^^^^^^^^^^^^^^^

William Kyngesburye provides a number of `geospatial library binary packages`__
that make it simple to get GeoDjango installed on OS X without compiling
them from source.  However, the `Apple Developer Tools`_ are still necessary
for compiling the Python database adapters :ref:`psycopg2_kyngchaos` (for PostGIS)
and :ref:`pysqlite2` (for SpatiaLite).

.. note::

    SpatiaLite users should consult the :ref:`spatialite_macosx` section
    after installing the packages for additional instructions.

Download the framework packages for:

* UnixImageIO
* PROJ
* GEOS
* SQLite3 (includes the SpatiaLite library)
* GDAL

Install the packages in the order they are listed above, as the GDAL and SQLite
packages require the packages listed before them.

Afterwards, you can also install the KyngChaos binary packages for `PostgreSQL
and PostGIS`__.

After installing the binary packages, you'll want to add the following to
your ``.profile`` to be able to run the package programs from the command-line::

    export PATH=/Library/Frameworks/UnixImageIO.framework/Programs:$PATH
    export PATH=/Library/Frameworks/PROJ.framework/Programs:$PATH
    export PATH=/Library/Frameworks/GEOS.framework/Programs:$PATH
    export PATH=/Library/Frameworks/SQLite3.framework/Programs:$PATH
    export PATH=/Library/Frameworks/GDAL.framework/Programs:$PATH
    export PATH=/usr/local/pgsql/bin:$PATH

__ http://www.kyngchaos.com/software/frameworks
__ http://www.kyngchaos.com/software/postgres

.. _psycopg2_kyngchaos:

psycopg2
~~~~~~~~

After you've installed the KyngChaos binaries and modified your ``PATH``, as
described above, ``psycopg2`` may be installed using the following command::

    $ sudo pip install psycopg2

.. note::

    If you don't have ``pip``, follow the :ref:`installation instructions
    <installing-official-release>` to install it.

.. _fink:

Fink
^^^^

`Kurt Schwehr`__ has been gracious enough to create GeoDjango packages for users
of the `Fink`__ package system.  The following packages are available, depending
on which version of Python you want to use:

* ``django-gis-py26``
* ``django-gis-py25``
* ``django-gis-py24``

__ http://schwehr.org/blog/
__ http://www.finkproject.org/

.. _macports:

MacPorts
^^^^^^^^

`MacPorts`__ may be used to install GeoDjango prerequisites on Macintosh
computers running OS X.  Because MacPorts still builds the software from source,
the `Apple Developer Tools`_ are required.

Summary::

    $ sudo port install postgresql83-server
    $ sudo port install geos
    $ sudo port install proj
    $ sudo port install postgis
    $ sudo port install gdal +geos
    $ sudo port install libgeoip

.. note::

    You will also have to modify the ``PATH`` in your ``.profile`` so
    that the MacPorts programs are accessible from the command-line::

        export PATH=/opt/local/bin:/opt/local/lib/postgresql83/bin

    In addition, add the ``DYLD_FALLBACK_LIBRARY_PATH`` setting so that
    the libraries can be found by Python::

        export DYLD_FALLBACK_LIBRARY_PATH=/opt/local/lib:/opt/local/lib/postgresql83

__ http://www.macports.org/

.. _windows:

Windows
-------

Proceed through the following sections sequentially in order to install
GeoDjango on Windows.

.. note::

    These instructions assume that you are using 32-bit versions of
    all programs.  While 64-bit versions of Python and PostgreSQL 9.x
    are available, 64-bit versions of spatial libraries, like
    GEOS and GDAL, are not yet provided by the :ref:`OSGeo4W` installer.

Python
^^^^^^

First, download the latest `Python 2.7 installer`__ from the Python Web site.
Next, run the installer and keep the defaults -- for example, keep
'Install for all users' checked and the installation path set as
``C:\Python27``.

.. note::

    You may already have a version of Python installed in ``C:\python`` as ESRI
    products sometimes install a copy there.  *You should still install a
    fresh version of Python 2.7.*

__ http://python.org/download/

PostgreSQL
^^^^^^^^^^

First, download the latest `PostgreSQL 9.x installer`__ from the
`EnterpriseDB`__ Web site.  After downloading, simply run the installer,
follow the on-screen directions, and keep the default options unless
you know the consequences of changing them.

.. note::

    The PostgreSQL installer creates both a new Windows user to be the
    'postgres service account' and a ``postgres`` database superuser
    You will be prompted once to set the password for both accounts --
    make sure to remember it!

When the installer completes, it will ask to launch the Application Stack
Builder (ASB) on exit -- keep this checked, as it is necessary to
install :ref:`postgisasb`.

.. note::

    If installed successfully, the PostgreSQL server will run in the
    background each time the system as started as a Windows service.
    A :menuselection:`PostgreSQL 9.x` start menu group will created
    and contains shortcuts for the ASB as well as the 'SQL Shell',
    which will launch a ``psql`` command window.

__ http://www.enterprisedb.com/products-services-training/pgdownload
__ http://www.enterprisedb.com

.. _postgisasb:

PostGIS
^^^^^^^

From within the Application Stack Builder (to run outside of the installer,
:menuselection:`Start --> Programs --> PostgreSQL 9.x`), select
:menuselection:`PostgreSQL Database Server 9.x on port 5432` from the drop down
menu.  Next, expand the :menuselection:`Categories --> Spatial Extensions` menu
tree and select :menuselection:`PostGIS 1.5 for PostgreSQL 9.x`.

After clicking next, you will be prompted to select your mirror, PostGIS
will be downloaded, and the PostGIS installer will begin.  Select only the
default options during install (e.g., do not uncheck the option to create a
default PostGIS database).

.. note::

    You will be prompted to enter your ``postgres`` database superuser
    password in the 'Database Connection Information' dialog.

psycopg2
^^^^^^^^

The ``psycopg2`` Python module provides the interface between Python and the
PostgreSQL database.  Download the latest `Windows installer`__ for your version
of Python and PostgreSQL and run using the default settings. [#]_

__ http://www.stickpeople.com/projects/python/win-psycopg/

.. _osgeo4w:

OSGeo4W
^^^^^^^

The `OSGeo4W installer`_ makes it simple to install the PROJ.4, GDAL, and GEOS
libraries required by GeoDjango.  First, download the `OSGeo4W installer`_,
and run it.  Select :menuselection:`Express Web-GIS Install` and click next.
In the 'Select Packages' list, ensure that GDAL is selected; MapServer and
Apache are also enabled by default, but are not required by GeoDjango and
may be unchecked safely.  After clicking next, the packages will be
automatically downloaded and installed, after which you may exit the
installer.

.. _OSGeo4W installer: http://trac.osgeo.org/osgeo4w/

Modify Windows environment
^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to use GeoDjango, you will need to add your Python and OSGeo4W
directories to your Windows system ``Path``, as well as create ``GDAL_DATA``
and ``PROJ_LIB`` environment variables.  The following set of commands,
executable with ``cmd.exe``, will set this up:

.. code-block:: bat

     set OSGEO4W_ROOT=C:\OSGeo4W
     set PYTHON_ROOT=C:\Python27
     set GDAL_DATA=%OSGEO4W_ROOT%\share\gdal
     set PROJ_LIB=%OSGEO4W_ROOT%\share\proj
     set PATH=%PATH%;%PYTHON_ROOT%;%OSGEO4W_ROOT%\bin
     reg ADD "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path /t REG_EXPAND_SZ /f /d "%PATH%"
     reg ADD "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v GDAL_DATA /t REG_EXPAND_SZ /f /d "%GDAL_DATA%"
     reg ADD "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PROJ_LIB /t REG_EXPAND_SZ /f /d "%PROJ_LIB%"

For your convenience, these commands are available in the executable batch
script, :download:`geodjango_setup.bat`.

.. note::

    Administrator privileges are required to execute these commands.
    To do this, right-click on :download:`geodjango_setup.bat` and select
    :menuselection:`Run as administrator`. You need to log out and log back in again
    for the settings to take effect.

.. note::

    If you customized the Python or OSGeo4W installation directories,
    then you will need to modify the ``OSGEO4W_ROOT`` and/or ``PYTHON_ROOT``
    variables accordingly.

Install Django and set up database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Finally, :ref:`install Django <installing-official-release>` on your system.

.. rubric:: Footnotes
.. [#] GeoDjango uses the :func:`~ctypes.util.find_library` routine from
       ``ctypes.util`` to locate shared libraries.
.. [#] The ``psycopg2`` Windows installers are packaged and maintained by
       `Jason Erickson <http://www.stickpeople.com/projects/python/win-psycopg/>`_.
