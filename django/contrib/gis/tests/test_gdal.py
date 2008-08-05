"""
Module for executing all of the GDAL tests.  None
of these tests require the use of the database.
"""
from unittest import TestSuite, TextTestRunner

# Importing the GDAL test modules.
from django.contrib.gis.tests import \
     test_gdal_driver, test_gdal_ds, test_gdal_envelope, \
     test_gdal_geom, test_gdal_srs
     

test_suites = [test_gdal_driver.suite(),
               test_gdal_ds.suite(),
               test_gdal_envelope.suite(),
               test_gdal_geom.suite(),
               test_gdal_srs.suite(),
               ]

def suite():
    "Builds a test suite for the GDAL tests."
    s = TestSuite()
    map(s.addTest, test_suites)
    return s

def run(verbosity=1):
    "Runs the GDAL tests."
    TextTestRunner(verbosity=verbosity).run(suite())
