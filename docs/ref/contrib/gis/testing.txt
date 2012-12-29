======================
Testing GeoDjango apps
======================

Included in this documentation are some additional notes and settings
for :ref:`testing-postgis` and :ref:`testing-spatialite` users.

.. _testing-postgis:

PostGIS
=======

Settings
--------

.. note::

    The settings below have sensible defaults, and shouldn't require manual setting.

.. setting:: POSTGIS_TEMPLATE

``POSTGIS_TEMPLATE``
^^^^^^^^^^^^^^^^^^^^

This setting may be used to customize the name of the PostGIS template
database to use. It automatically defaults to ``'template_postgis'``
(the same name used in the
:ref:`installation documentation <spatialdb_template>`).

.. setting:: POSTGIS_VERSION

``POSTGIS_VERSION``
^^^^^^^^^^^^^^^^^^^

When GeoDjango's spatial backend initializes on PostGIS, it has to perform
a SQL query to determine the version in order to figure out what
features are available. Advanced users wishing to prevent this additional
query may set the version manually using a 3-tuple of integers specifying
the major, minor, and subminor version numbers for PostGIS. For example,
to configure for PostGIS 1.5.2 you would use::

    POSTGIS_VERSION = (1, 5, 2)

Obtaining sufficient privileges
-------------------------------

Depending on your configuration, this section describes several methods to
configure a database user with sufficient privileges to run tests for
GeoDjango applications on PostgreSQL. If your
:ref:`spatial database template <spatialdb_template>`
was created like in the instructions, then your testing database user
only needs to have the ability to create databases. In other configurations,
you may be required to use a database superuser.

Create database user
^^^^^^^^^^^^^^^^^^^^

To make a database user with the ability to create databases, use the
following command::

    $ createuser --createdb -R -S <user_name>

The ``-R -S`` flags indicate that we do not want the user to have the ability
to create additional users (roles) or to be a superuser, respectively.

Alternatively, you may alter an existing user's role from the SQL shell
(assuming this is done from an existing superuser account)::

    postgres# ALTER ROLE <user_name> CREATEDB NOSUPERUSER NOCREATEROLE;

Create database superuser
^^^^^^^^^^^^^^^^^^^^^^^^^

This may be done at the time the user is created, for example::

    $ createuser --superuser <user_name>

Or you may alter the user's role from the SQL shell (assuming this
is done from an existing superuser account)::

    postgres# ALTER ROLE <user_name> SUPERUSER;


Create local PostgreSQL database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Initialize database: ``initdb -D /path/to/user/db``

2. If there's already a Postgres instance on the machine, it will need
   to use a different TCP port than 5432. Edit ``postgresql.conf`` (in
   ``/path/to/user/db``) to change the database port (e.g. ``port = 5433``).

3. Start this database ``pg_ctl -D /path/to/user/db start``

Windows
-------

On Windows platforms the pgAdmin III utility may also be used as
a simple way to add superuser privileges to your database user.

By default, the PostGIS installer on Windows includes a template
spatial database entitled ``template_postgis``.

.. _testing-spatialite:

SpatiaLite
==========

Make sure the necessary spatial tables are created in your test spatial
database, as described in :ref:`create_spatialite_db`. Then just do this::

    $ python manage.py test

Settings
--------

.. setting:: SPATIALITE_SQL

``SPATIALITE_SQL``
^^^^^^^^^^^^^^^^^^

Only relevant when using a SpatiaLite version 2.3.

By default, the GeoDjango test runner looks for the :ref:`file containing the
SpatiaLite dababase-initialization SQL code <create_spatialite_db>` in the
same directory where it was invoked (by default the same directory where
``manage.py`` is located). To use a different location, add the following to
your settings::

    SPATIALITE_SQL='/path/to/init_spatialite-2.3.sql'

.. _geodjango-tests:

GeoDjango tests
===============

GeoDjango's test suite may be run in one of two ways, either by itself or
with the rest of :ref:`Django's unit tests <running-unit-tests>`.

Run only GeoDjango tests
------------------------

.. class:: django.contrib.gis.tests.GeoDjangoTestSuiteRunner

To run *only* the tests for GeoDjango, the :setting:`TEST_RUNNER`
setting must be changed to use the
:class:`~django.contrib.gis.tests.GeoDjangoTestSuiteRunner`::

    TEST_RUNNER = 'django.contrib.gis.tests.GeoDjangoTestSuiteRunner'

Example
^^^^^^^

First, you'll need a bare-bones settings file, like below, that is
customized with your spatial database name and user::

    TEST_RUNNER = 'django.contrib.gis.tests.GeoDjangoTestSuiteRunner'

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'a_spatial_database',
            'USER': 'db_user'
        }
    }

Assuming the above is in a file called ``postgis.py`` that is in the
the same directory as ``manage.py`` of your Django project, then
you may run the tests with the following command::

    $ python manage.py test --settings=postgis

Run with ``runtests.py``
------------------------

To have the GeoDjango tests executed when
:ref:`running the Django test suite <running-unit-tests>` with ``runtests.py``
all of the databases in the settings file must be using one of the
:ref:`spatial database backends <spatial-backends>`.

.. warning::

    Do not change the :setting:`TEST_RUNNER` setting
    when running the GeoDjango tests with ``runtests.py``.

Example
^^^^^^^

The following is an example bare-bones settings file with spatial backends
that can be used to run the entire Django test suite, including those
in :mod:`django.contrib.gis`::

    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'geodjango',
            'USER': 'geodjango',
        },
       'other': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'other',
            'USER': 'geodjango',
       }
    }

Assuming the settings above were in a ``postgis.py`` file in the same
directory as ``runtests.py``, then all Django and GeoDjango tests would
be performed when executing the command::

    $ ./runtests.py --settings=postgis
