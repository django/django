from django.conf import settings
from django.test.simple import build_suite, DjangoTestSuiteRunner
from django.utils import unittest

def run_tests(*args, **kwargs):
    from django.test.simple import run_tests as base_run_tests
    return base_run_tests(*args, **kwargs)


def run_gis_tests(test_labels, verbosity=1, interactive=True, failfast=False, extra_tests=None):
    import warnings
    warnings.warn(
        'The run_gis_tests() test runner has been deprecated in favor of GeoDjangoTestSuiteRunner.',
        DeprecationWarning
    )
    test_runner = GeoDjangoTestSuiteRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
    return test_runner.run_tests(test_labels, extra_tests=extra_tests)


def geo_apps(namespace=True, runtests=False):
    """
    Returns a list of GeoDjango test applications that reside in
    `django.contrib.gis.tests` that can be used with the current
    database and the spatial libraries that are installed.
    """
    from django.db import connection
    from django.contrib.gis.geos import GEOS_PREPARE
    from django.contrib.gis.gdal import HAS_GDAL

    apps = ['geoapp', 'relatedapp']

    # No distance queries on MySQL.
    if not connection.ops.mysql:
        apps.append('distapp')

    # Test geography support with PostGIS 1.5+.
    if connection.ops.postgis and connection.ops.geography:
        apps.append('geogapp')

    # The following GeoDjango test apps depend on GDAL support.
    if HAS_GDAL:
        # 3D apps use LayerMapping, which uses GDAL.
        if connection.ops.postgis and GEOS_PREPARE:
            apps.append('geo3d')

        apps.append('layermap')

    if runtests:
        return [('django.contrib.gis.tests', app) for app in apps]
    elif namespace:
        return ['django.contrib.gis.tests.%s' % app
                for app in apps]
    else:
        return apps


def geodjango_suite(apps=True):
    """
    Returns a TestSuite consisting only of GeoDjango tests that can be run.
    """
    import sys
    from django.db.models import get_app

    suite = unittest.TestSuite()

    # Adding the GEOS tests.
    from django.contrib.gis.geos import tests as geos_tests
    suite.addTest(geos_tests.suite())

    # Adding the measurment tests.
    from django.contrib.gis.tests import test_measure
    suite.addTest(test_measure.suite())

    # Adding GDAL tests, and any test suite that depends on GDAL, to the
    # suite if GDAL is available.
    from django.contrib.gis.gdal import HAS_GDAL
    if HAS_GDAL:
        from django.contrib.gis.gdal import tests as gdal_tests
        suite.addTest(gdal_tests.suite())

        from django.contrib.gis.tests import test_spatialrefsys, test_geoforms
        suite.addTest(test_spatialrefsys.suite())
        suite.addTest(test_geoforms.suite())
    else:
        sys.stderr.write('GDAL not available - no tests requiring GDAL will be run.\n')

    # Add GeoIP tests to the suite, if the library and data is available.
    from django.contrib.gis.utils import HAS_GEOIP
    if HAS_GEOIP and hasattr(settings, 'GEOIP_PATH'):
        from django.contrib.gis.tests import test_geoip
        suite.addTest(test_geoip.suite())

    # Finally, adding the suites for each of the GeoDjango test apps.
    if apps:
        for app_name in geo_apps(namespace=False):
            suite.addTest(build_suite(get_app(app_name)))

    return suite


class GeoDjangoTestSuiteRunner(DjangoTestSuiteRunner):

    def setup_test_environment(self, **kwargs):
        super(GeoDjangoTestSuiteRunner, self).setup_test_environment(**kwargs)

        # Saving original values of INSTALLED_APPS, ROOT_URLCONF, and SITE_ID.
        self.old_installed = getattr(settings, 'INSTALLED_APPS', None)
        self.old_root_urlconf = getattr(settings, 'ROOT_URLCONF', '')
        self.old_site_id = getattr(settings, 'SITE_ID', None)

        # Constructing the new INSTALLED_APPS, and including applications
        # within the GeoDjango test namespace.
        new_installed =  ['django.contrib.sites',
                          'django.contrib.sitemaps',
                          'django.contrib.gis',
                          ]

        # Calling out to `geo_apps` to get GeoDjango applications supported
        # for testing.
        new_installed.extend(geo_apps())
        settings.INSTALLED_APPS = new_installed

        # SITE_ID needs to be set
        settings.SITE_ID = 1

        # ROOT_URLCONF needs to be set, else `AttributeErrors` are raised
        # when TestCases are torn down that have `urls` defined.
        settings.ROOT_URLCONF = ''


    def teardown_test_environment(self, **kwargs):
        super(GeoDjangoTestSuiteRunner, self).teardown_test_environment(**kwargs)
        settings.INSTALLED_APPS = self.old_installed
        settings.ROOT_URLCONF = self.old_root_urlconf
        settings.SITE_ID = self.old_site_id


    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        return geodjango_suite()
