import sys, unittest
from django.test.simple import run_tests
from django.utils.importlib import import_module

def geo_suite():
    """
    Builds a test suite for the GIS package.  This is not named
    `suite` so it will not interfere with the Django test suite (since
    spatial database tables are required to execute these tests on
    some backends).
    """
    from django.conf import settings
    from django.contrib.gis.geos import GEOS_PREPARE
    from django.contrib.gis.gdal import HAS_GDAL
    from django.contrib.gis.utils import HAS_GEOIP
    from django.contrib.gis.tests.utils import postgis, mysql

    gis_tests = []

    # Adding the GEOS tests.
    from django.contrib.gis.geos import tests as geos_tests
    gis_tests.append(geos_tests.suite())

    # Tests that require use of a spatial database (e.g., creation of models)
    test_apps = ['geoapp', 'relatedapp']

    # Tests that do not require setting up and tearing down a spatial database.
    test_suite_names = [
        'test_measure',
        ]

    # Tests applications that require a test spatial db.
    if not mysql:
        test_apps.append('distapp')

    # Only PostGIS using GEOS 3.1+ can support 3D so far.
    if postgis and GEOS_PREPARE:
        test_apps.append('geo3d')

    if HAS_GDAL:
        # These tests require GDAL.
        test_suite_names.extend(['test_spatialrefsys', 'test_geoforms'])
        test_apps.append('layermap')

        # Adding the GDAL tests.
        from django.contrib.gis.gdal import tests as gdal_tests
        gis_tests.append(gdal_tests.suite())
    else:
        print >>sys.stderr, "GDAL not available - no tests requiring GDAL will be run."

    if HAS_GEOIP and hasattr(settings, 'GEOIP_PATH'):
        test_suite_names.append('test_geoip')

    # Adding the rest of the suites from the modules specified
    # in the `test_suite_names`.
    for suite_name in test_suite_names:
        tsuite = import_module('django.contrib.gis.tests.' + suite_name)
        gis_tests.append(tsuite.suite())

    return gis_tests, test_apps

def run_gis_tests(test_labels, **kwargs):
    """
    Use this routine as the TEST_RUNNER in your settings in order to run the
    GeoDjango test suite.  This must be done as a database superuser for
    PostGIS, so read the docstring in `run_test()` below for more details.
    """
    from django.conf import settings
    from django.db.models import loading
    from django.contrib.gis.tests.utils import mysql

    # Getting initial values.
    old_installed = settings.INSTALLED_APPS
    old_root_urlconf = settings.ROOT_URLCONF

    # Overridding the INSTALLED_APPS with only what we need,
    # to prevent unnecessary database table creation.
    new_installed =  ['django.contrib.sites',
                      'django.contrib.sitemaps',
                      'django.contrib.gis',
                      ]

    # Setting the URLs.
    settings.ROOT_URLCONF = 'django.contrib.gis.tests.urls'

    # Creating the test suite, adding the test models to INSTALLED_APPS
    # so they will be tested.
    gis_tests, test_apps = geo_suite()
    for test_model in test_apps:
        module_name = 'django.contrib.gis.tests.%s' % test_model
        new_installed.append(module_name)

    # Resetting the loaded flag to take into account what we appended to
    # the INSTALLED_APPS (since this routine is invoked through
    # django/core/management, it caches the apps; this ensures that syncdb
    # will see our appended models)
    settings.INSTALLED_APPS = new_installed
    loading.cache.loaded = False

    kwargs['extra_tests'] = gis_tests

    # Running the tests using the GIS test runner.
    result = run_tests(test_labels, **kwargs)

    # Restoring modified settings.
    settings.INSTALLED_APPS = old_installed
    settings.ROOT_URLCONF = old_root_urlconf

    return result
