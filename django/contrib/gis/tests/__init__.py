import sys
from copy import copy
from unittest import TestSuite, TextTestRunner

from django.conf import settings
if not settings._target: settings.configure()

def geo_suite():
    """
    Builds a test suite for the GIS package.  This is not named
    `suite` so it will not interfere with the Django test suite (since
    spatial database tables are required to execute these tests on
    some backends).
    """
    from django.contrib.gis.tests.utils import mysql, oracle, postgis
    from django.contrib.gis.gdal import HAS_GDAL
    from django.contrib.gis.utils import HAS_GEOIP

    # Tests that require use of a spatial database (e.g., creation of models)
    test_models = ['geoapp',]

    # Tests that do not require setting up and tearing down a spatial database.
    test_suite_names = [
        'test_geos',
        'test_measure',
        ]
    if HAS_GDAL:
        if oracle:
            # TODO: There's a problem with `select_related` and GeoQuerySet on
            # Oracle -- e.g., GeoModel.objects.distance(geom, field_name='fk__point')
            # doesn't work so we don't test `relatedapp`.
            test_models += ['distapp', 'layermap']
        elif postgis:
            test_models += ['distapp', 'layermap', 'relatedapp']
        elif mysql:
            test_models += ['relatedapp']

        test_suite_names += [
            'test_gdal_driver',
            'test_gdal_ds',
            'test_gdal_envelope',
            'test_gdal_geom',
            'test_gdal_srs',
            'test_spatialrefsys',
            ]
    else:
        print >>sys.stderr, "GDAL not available - no GDAL tests will be run."

    if HAS_GEOIP and hasattr(settings, 'GEOIP_PATH'):
        test_suite_names.append('test_geoip')

    s = TestSuite()
    for test_suite in test_suite_names:
        tsuite = getattr(__import__('django.contrib.gis.tests', globals(), locals(), [test_suite]),test_suite)
        s.addTest(tsuite.suite())
    return s, test_models

def run(verbosity=1):
    "Runs the tests that do not require geographic (GEOS, GDAL, etc.) models."
    TextTestRunner(verbosity=verbosity).run(geo_suite())

def run_tests(module_list, verbosity=1, interactive=True):
    """
    Run the tests that require creation of a spatial database.
    
    In order to run geographic model tests the DATABASE_USER will require
    superuser priviliges.  To accomplish this outside the `postgres` user,
    create your own PostgreSQL database as a user:
     (1) Initialize database: `initdb -D /path/to/user/db`
     (2) If there's already a Postgres instance on the machine, it will need
         to use a different TCP port than 5432. Edit postgresql.conf (in 
         /path/to/user/db) to change the database port (e.g. `port = 5433`).  
     (3) Start this database `pg_ctl -D /path/to/user/db start`

    On Windows platforms simply use the pgAdmin III utility to add superuser 
    privileges to your database user.

    Make sure your settings.py matches the settings of the user database. 
    For example, set the same port number (`DATABASE_PORT=5433`).  
    DATABASE_NAME or TEST_DATABSE_NAME must be set, along with DATABASE_USER.
      
    In settings.py set TEST_RUNNER='django.contrib.gis.tests.run_tests'.

    Finally, this assumes that the PostGIS SQL files (lwpostgis.sql and 
    spatial_ref_sys.sql) are installed in the directory specified by 
    `pg_config --sharedir` (and defaults to /usr/local/share if that fails).
    This behavior is overridden if `POSTGIS_SQL_PATH` is in your settings.
    
    Windows users should set POSTGIS_SQL_PATH manually because the output
    of `pg_config` uses paths like 'C:/PROGRA~1/POSTGR~1/..'.

    Finally, the tests may be run by invoking `./manage.py test`.
    """
    from django.contrib.gis.db.backend import create_spatial_db
    from django.contrib.gis.tests.utils import mysql
    from django.db import connection

    # Getting initial values.
    old_debug = settings.DEBUG
    old_name = copy(settings.DATABASE_NAME)
    old_installed = copy(settings.INSTALLED_APPS)
    new_installed = copy(settings.INSTALLED_APPS)

    # Want DEBUG to be set to False.
    settings.DEBUG = False

    from django.db.models import loading

    # Creating the test suite, adding the test models to INSTALLED_APPS, and
    #  adding the model test suites to our suite package.
    test_suite, test_models = geo_suite()
    for test_model in test_models:
        module_name = 'django.contrib.gis.tests.%s' % test_model
        if mysql:
            test_module_name = 'tests_mysql'
        else:
            test_module_name = 'tests'
        new_installed.append(module_name)

        # Getting the test suite
        tsuite = getattr(__import__('django.contrib.gis.tests.%s' % test_model, globals(), locals(), [test_module_name]), test_module_name)
        test_suite.addTest(tsuite.suite())
    
    # Resetting the loaded flag to take into account what we appended to 
    # the INSTALLED_APPS (since this routine is invoked through 
    # django/core/management, it caches the apps; this ensures that syncdb 
    # will see our appended models)
    settings.INSTALLED_APPS = new_installed
    loading.cache.loaded = False

    # Creating the test spatial database.
    create_spatial_db(test=True, verbosity=verbosity)

    # Executing the tests (including the model tests)
    result = TextTestRunner(verbosity=verbosity).run(test_suite)

    # Cleaning up, destroying the test spatial database and resetting the INSTALLED_APPS.
    connection.creation.destroy_test_db(old_name, verbosity)
    settings.DEBUG = old_debug
    settings.INSTALLED_APPS = old_installed
    
    # Returning the total failures and errors
    return len(result.failures) + len(result.errors)

if __name__ == '__main__':
    run()
