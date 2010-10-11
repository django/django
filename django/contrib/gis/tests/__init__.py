import sys

from django.conf import settings
from django.db.models import get_app
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

class GeoDjangoTestSuiteRunner(DjangoTestSuiteRunner):

    def setup_test_environment(self, **kwargs):
        super(GeoDjangoTestSuiteRunner, self).setup_test_environment(**kwargs)

        from django.db import connection
        from django.contrib.gis.geos import GEOS_PREPARE
        from django.contrib.gis.gdal import HAS_GDAL

        # Getting and storing the original values of INSTALLED_APPS and
        # the ROOT_URLCONF.
        self.old_installed = settings.INSTALLED_APPS
        self.old_root_urlconf = settings.ROOT_URLCONF

        # Tests that require use of a spatial database (e.g., creation of models)
        self.geo_apps = ['geoapp', 'relatedapp']
        if connection.ops.postgis and connection.ops.geography:
            # Test geography support with PostGIS 1.5+.
            self.geo_apps.append('geogapp')

        if HAS_GDAL:
            # The following GeoDjango test apps depend on GDAL support.
            if not connection.ops.mysql:
                self.geo_apps.append('distapp')

            # 3D apps use LayerMapping, which uses GDAL.
            if connection.ops.postgis and GEOS_PREPARE:
                self.geo_apps.append('geo3d')

            self.geo_apps.append('layermap')

        # Constructing the new INSTALLED_APPS, and including applications
        # within the GeoDjango test namespace (`self.geo_apps`).
        new_installed =  ['django.contrib.sites',
                          'django.contrib.sitemaps',
                          'django.contrib.gis',
                          ]
        new_installed.extend(['django.contrib.gis.tests.%s' % app
                              for app in self.geo_apps])
        settings.INSTALLED_APPS = new_installed

        # Setting the URLs.
        settings.ROOT_URLCONF = 'django.contrib.gis.tests.urls'

    def teardown_test_environment(self, **kwargs):
        super(GeoDjangoTestSuiteRunner, self).teardown_test_environment(**kwargs)
        settings.INSTALLED_APPS = self.old_installed
        settings.ROOT_URLCONF = self.old_root_urlconf

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        """
        This method is overridden to construct a suite consisting only of tests
        for GeoDjango.
        """
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
        for app_name in self.geo_apps:
            suite.addTest(build_suite(get_app(app_name)))

        return suite
