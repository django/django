.. _postgis:

==================
Installing PostGIS
==================

`PostGIS`__ adds geographic object support to PostgreSQL, turning it
into a spatial database. :ref:`geosbuild`, :ref:`proj4` and
:ref:`gdalbuild` should be installed prior to building PostGIS. You
might also need additional libraries, see `PostGIS requirements`_.

.. note::

    The `psycopg2`_ module is required for use as the database adaptor
    when using GeoDjango with PostGIS.

.. _psycopg2: http://initd.org/psycopg/
.. _PostGIS requirements: http://www.postgis.org/documentation/manual-2.0/postgis_installation.html#id2711662

On Debian/Ubuntu, you are advised to install the following packages:
postgresql-x.x, postgresql-x.x-postgis, postgresql-server-dev-x.x,
python-psycopg2 (x.x matching the PostgreSQL version you want to install).
Please also consult platform-specific instructions if you are on :ref:`macosx`
or :ref:`windows`.

Building from source
====================

First download the source archive, and extract::

    $ wget http://postgis.refractions.net/download/postgis-2.0.1.tar.gz
    $ tar xzf postgis-2.0.1.tar.gz
    $ cd postgis-2.0.1

Next, configure, make and install PostGIS::

    $ ./configure

Finally, make and install::

    $ make
    $ sudo make install
    $ cd ..

.. note::

    GeoDjango does not automatically create a spatial database.  Please consult
    the section on :ref:`spatialdb_template91` or
    :ref:`spatialdb_template_earlier` for more information.

__ http://postgis.refractions.net/

Post-installation
=================

.. _spatialdb_template:
.. _spatialdb_template91:

Creating a spatial database with PostGIS 2.0 and PostgreSQL 9.1+
----------------------------------------------------------------

PostGIS 2 includes an extension for Postgres 9.1+ that can be used to enable
spatial functionality::

    $ createdb  <db name>
    $ psql <db name>
    > CREATE EXTENSION postgis;
    > CREATE EXTENSION postgis_topology;

No PostGIS topology functionalities are yet available from GeoDjango, so the
creation of the ``postgis_topology`` extension is entirely optional.

.. _spatialdb_template_earlier:

Creating a spatial database template for earlier versions
---------------------------------------------------------

If you have an earlier version of PostGIS or PostgreSQL, the CREATE
EXTENSION isn't available and you need to create the spatial database
using the following instructions.

Creating a spatial database with PostGIS is different than normal because
additional SQL must be loaded to enable spatial functionality.  Because of
the steps in this process, it's better to create a database template that
can be reused later.

First, you need to be able to execute the commands as a privileged database
user.  For example, you can use the following to become the ``postgres`` user::

    $ sudo su - postgres

.. note::

   The location *and* name of the PostGIS SQL files (e.g., from
   ``POSTGIS_SQL_PATH`` below) depends on the version of PostGIS.
   PostGIS versions 1.3 and below use ``<pg_sharedir>/contrib/lwpostgis.sql``;
   whereas version 1.4 uses ``<sharedir>/contrib/postgis.sql`` and
   version 1.5 uses ``<sharedir>/contrib/postgis-1.5/postgis.sql``.

   To complicate matters, Debian/Ubuntu distributions have their own separate
   directory naming system that might change with time. In this case, use the
   :download:`create_template_postgis-debian.sh` script.

   The example below assumes PostGIS 1.5, thus you may need to modify
   ``POSTGIS_SQL_PATH`` and the name of the SQL file for the specific
   version of PostGIS you are using.

Once you're a database super user, then you may execute the following commands
to create a PostGIS spatial database template::

    $ POSTGIS_SQL_PATH=`pg_config --sharedir`/contrib/postgis-2.0
    # Creating the template spatial database.
    $ createdb -E UTF8 template_postgis
    $ createlang -d template_postgis plpgsql # Adding PLPGSQL language support.
    # Allows non-superusers the ability to create from this template
    $ psql -d postgres -c "UPDATE pg_database SET datistemplate='true' WHERE datname='template_postgis';"
    # Loading the PostGIS SQL routines
    $ psql -d template_postgis -f $POSTGIS_SQL_PATH/postgis.sql
    $ psql -d template_postgis -f $POSTGIS_SQL_PATH/spatial_ref_sys.sql
    # Enabling users to alter spatial tables.
    $ psql -d template_postgis -c "GRANT ALL ON geometry_columns TO PUBLIC;"
    $ psql -d template_postgis -c "GRANT ALL ON geography_columns TO PUBLIC;"
    $ psql -d template_postgis -c "GRANT ALL ON spatial_ref_sys TO PUBLIC;"

These commands may be placed in a shell script for later use; for convenience
the following scripts are available:

===============  =============================================
PostGIS version  Bash shell script
===============  =============================================
1.3              :download:`create_template_postgis-1.3.sh`
1.4              :download:`create_template_postgis-1.4.sh`
1.5              :download:`create_template_postgis-1.5.sh`
Debian/Ubuntu    :download:`create_template_postgis-debian.sh`
===============  =============================================

Afterwards, you may create a spatial database by simply specifying
``template_postgis`` as the template to use (via the ``-T`` option)::

    $ createdb -T template_postgis <db name>

.. note::

    While the ``createdb`` command does not require database super-user privileges,
    it must be executed by a database user that has permissions to create databases.
    You can create such a user with the following command::

        $ createuser --createdb <user>

PostgreSQL's createdb fails
---------------------------

When the PostgreSQL cluster uses a non-UTF8 encoding, the
:file:`create_template_postgis-*.sh` script will fail when executing
``createdb``::

    createdb: database creation failed: ERROR:  new encoding (UTF8) is incompatible
      with the encoding of the template database (SQL_ASCII)

The `current workaround`__ is to re-create the cluster using UTF8 (back up any
databases before dropping the cluster).

__ http://jacobian.org/writing/pg-encoding-ubuntu/

Managing the database
---------------------

To administer the database, you can either use the pgAdmin III program
(:menuselection:`Start --> PostgreSQL 9.x --> pgAdmin III`) or the
SQL Shell (:menuselection:`Start --> PostgreSQL 9.x --> SQL Shell`).
For example, to create a ``geodjango`` spatial database and user, the following
may be executed from the SQL Shell as the ``postgres`` user::

    postgres# CREATE USER geodjango PASSWORD 'my_passwd';
    postgres# CREATE DATABASE geodjango OWNER geodjango TEMPLATE template_postgis ENCODING 'utf8';
