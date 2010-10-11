"""
Module for executing all of the GDAL tests.  None
of these tests require the use of the database.
"""
from django.utils.unittest import TestSuite, TextTestRunner

# Importing the GDAL test modules.
import test_driver, test_ds, test_envelope, test_geom, test_srs

test_suites = [test_driver.suite(),
               test_ds.suite(),
               test_envelope.suite(),
               test_geom.suite(),
               test_srs.suite(),
               ]

def suite():
    "Builds a test suite for the GDAL tests."
    s = TestSuite()
    map(s.addTest, test_suites)
    return s

def run(verbosity=1):
    "Runs the GDAL tests."
    TextTestRunner(verbosity=verbosity).run(suite())
