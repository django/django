.. _spatialite:

=====================
Installing Spatialite
=====================

`SpatiaLite`__ adds spatial support to SQLite, turning it into a full-featured
spatial database.

Check first if you can install Spatialite from system packages or binaries. For
example, on Debian-based distributions, try to install the ``spatialite-bin``
package. For Mac OS X, follow the
:ref:`specific instructions below<spatialite_macosx>`. For Windows, you may
find binaries on `Gaia-SINS`__ home page. In any case, you should always
be able to :ref:`install from source<spatialite_source>`.

When you are done with the installation process, skip to :ref:`create_spatialite_db`.

__ https://www.gaia-gis.it/fossil/libspatialite
__ http://www.gaia-gis.it/gaia-sins/

.. _spatialite_source:

Installing from source
~~~~~~~~~~~~~~~~~~~~~~

:ref:`GEOS and PROJ.4<geospatial_libs>` should be installed prior to building
SpatiaLite.

SQLite
^^^^^^

Check first if SQLite is compiled with the `R*Tree module`__. Run the sqlite3
command line interface and enter the following query::

    sqlite> CREATE VIRTUAL TABLE testrtree USING rtree(id,minX,maxX,minY,maxY);

If you obtain an error, you will have to recompile SQLite from source. Otherwise,
just skip this section.

To install from sources, download the latest amalgamation source archive from
the `SQLite download page`__, and extract::

    $ wget http://sqlite.org/sqlite-amalgamation-3.6.23.1.tar.gz
    $ tar xzf sqlite-amalgamation-3.6.23.1.tar.gz
    $ cd sqlite-3.6.23.1

Next, run the ``configure`` script -- however the ``CFLAGS`` environment variable
needs to be customized so that SQLite knows to build the R*Tree module::

    $ CFLAGS="-DSQLITE_ENABLE_RTREE=1" ./configure
    $ make
    $ sudo make install
    $ cd ..

__ http://www.sqlite.org/rtree.html
__ http://www.sqlite.org/download.html

.. _spatialitebuild:

SpatiaLite library (``libspatialite``) and tools (``spatialite``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Get the latest SpatiaLite library source and tools bundle from the
`download page`__::

    $ wget http://www.gaia-gis.it/gaia-sins/libspatialite-sources/libspatialite-amalgamation-2.4.0-5.tar.gz
    $ wget http://www.gaia-gis.it/gaia-sins/spatialite-tools-sources/spatialite-tools-2.4.0-5.tar.gz
    $ tar xzf libspatialite-amalgamation-2.4.0-5.tar.gz
    $ tar xzf spatialite-tools-2.4.0-5.tar.gz

Prior to attempting to build, please read the important notes below to see if
customization of the ``configure`` command is necessary.  If not, then run the
``configure`` script, make, and install for the SpatiaLite library::

    $ cd libspatialite-amalgamation-2.3.1
    $ ./configure # May need to be modified, see notes below.
    $ make
    $ sudo make install
    $ cd ..

.. _spatialite_tools:

Finally, do the same for the SpatiaLite tools::

    $ cd spatialite-tools-2.3.1
    $ ./configure # May need to be modified, see notes below.
    $ make
    $ sudo make install
    $ cd ..

.. note::

    If you've installed GEOS and PROJ.4 from binary packages, you will have to specify
    their paths when running the ``configure`` scripts for *both* the library and the
    tools (the configure scripts look, by default, in ``/usr/local``).  For example,
    on Debian/Ubuntu distributions that have GEOS and PROJ.4 packages, the command would be::

       $ ./configure --with-proj-include=/usr/include --with-proj-lib=/usr/lib --with-geos-include=/usr/include --with-geos-lib=/usr/lib

.. note::

    For Mac OS X users building from source, the SpatiaLite library *and* tools
    need to have their ``target`` configured::

        $ ./configure --target=macosx

__ http://www.gaia-gis.it/gaia-sins/libspatialite-sources/

.. _spatialite_macosx:

Mac OS X-specific instructions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mac OS X users should follow the instructions in the :ref:`kyngchaos` section,
as it is much easier than building from source.

When :ref:`create_spatialite_db`, the ``spatialite`` program is required.
However, instead of attempting to compile the SpatiaLite tools from source,
download the `SpatiaLite Binaries`__ for OS X, and install ``spatialite`` in a
location available in your ``PATH``.  For example::

    $ curl -O http://www.gaia-gis.it/spatialite/spatialite-tools-osx-x86-2.3.1.tar.gz
    $ tar xzf spatialite-tools-osx-x86-2.3.1.tar.gz
    $ cd spatialite-tools-osx-x86-2.3.1/bin
    $ sudo cp spatialite /Library/Frameworks/SQLite3.framework/Programs

Finally, for GeoDjango to be able to find the KyngChaos SpatiaLite library,
add the following to your ``settings.py``:

.. code-block:: python

    SPATIALITE_LIBRARY_PATH='/Library/Frameworks/SQLite3.framework/SQLite3'

__ http://www.gaia-gis.it/spatialite-2.3.1/binaries.html

.. _create_spatialite_db:

Creating a spatial database for SpatiaLite
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After you've installed SpatiaLite, you'll need to create a number of spatial
metadata tables in your database in order to perform spatial queries.

If you're using SpatiaLite 2.4 or newer, use the ``spatialite`` utility to
call the ``InitSpatialMetaData()`` function, like this::

   $ spatialite geodjango.db "SELECT InitSpatialMetaData();"
   the SPATIAL_REF_SYS table already contains some row(s)
    InitSpatiaMetaData ()error:"table spatial_ref_sys already exists"
   0

You can safely ignore the error messages shown. When you've done this, you can
skip the rest of this section.

If you're using SpatiaLite 2.3, you'll need to download a
database-initialization file and execute its SQL queries in your database.

First, get it from the `SpatiaLite Resources`__ page::

   $ wget http://www.gaia-gis.it/spatialite-2.3.1/init_spatialite-2.3.sql.gz
   $ gunzip init_spatialite-2.3.sql.gz

Then, use the ``spatialite`` command to initialize a spatial database::

   $ spatialite geodjango.db < init_spatialite-2.3.sql

.. note::

    The parameter ``geodjango.db`` is the *filename* of the SQLite database
    you want to use.  Use the same in the :setting:`DATABASES` ``"name"`` key
    inside your ``settings.py``.

__ http://www.gaia-gis.it/spatialite-2.3.1/resources.html
