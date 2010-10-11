"""
GEOS Testing module.
"""
from django.utils.unittest import TestSuite, TextTestRunner
import test_geos, test_io, test_geos_mutation, test_mutable_list

test_suites = [
    test_geos.suite(),
    test_io.suite(),
    test_geos_mutation.suite(),
    test_mutable_list.suite(),
    ]

def suite():
    "Builds a test suite for the GEOS tests."
    s = TestSuite()
    map(s.addTest, test_suites)
    return s

def run(verbosity=1):
    "Runs the GEOS tests."
    TextTestRunner(verbosity=verbosity).run(suite())

if __name__ == '__main__':
    run(2)
