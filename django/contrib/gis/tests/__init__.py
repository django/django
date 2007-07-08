from unittest import TestSuite, makeSuite, TextTestRunner

test_suite_names = ['test_gdal_driver',
              'test_gdal_ds',
              'test_gdal_geom',
              'test_gdal_srs',
              'test_geos',
              'test_measure',
              'test_spatialrefsys',
               ]


def suite():
    s = TestSuite()
    for test_suite in test_suite_names:
        suite = getattr(__import__('django.contrib.gis.tests', fromlist=[test_suite]),test_suite)
        s.addTest(suite.suite())
    return s

def run(verbosity=1):
    TextTestRunner(verbosity=verbosity).run(suite())

if __name__ == '__main__':
    run()
